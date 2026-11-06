"""Read-only MCP stdio service with an optional loopback browser observatory."""
import argparse
import base64
import json
import sys
from threading import Thread

from ..observer.agent_feed import add_viewer_options, configured_feed
from .readonly import Adapter, Refusal, configuration, TOOLS

ID = {'type':'string','pattern':'^[A-Za-z0-9_-]{1,64}$','maxLength':64}
SPAN = {'type':'object','additionalProperties':False,
        'required':['region_id','offset','length'],
        'properties':{'region_id':ID,'offset':{'type':'integer','minimum':0,'maximum':4095},
                      'length':{'type':'integer','minimum':1,'maximum':512}}}
SCHEMAS = {}
for name in TOOLS:
    fields = {} if name == 'list_instances' else {'instance_id':ID}
    required = list(fields)
    if name in ('read_memory','observe_machine'):
        fields.update(expected_generation={'type':'integer','minimum':1},
                      expected_session={'type':'string','pattern':'^[a-f0-9]{32}$','maxLength':32})
    if name == 'read_memory':
        fields.update(SPAN['properties'])
        required += ['region_id','offset','length','expected_generation','expected_session']
    if name == 'observe_machine':
        fields.update(memory={'type':'array','maxItems':4,'items':SPAN},
                      include_text={'type':'boolean','default':True},
                      include_framebuffer={'type':'boolean','default':False})
    SCHEMAS[name] = {'type':'object','additionalProperties':False,
                     'properties':fields,'required':required}

DESCRIPTIONS = {
    'list_instances':'List only owner-configured IDs; does not discover or probe processes.',
    'get_instance_status':'Non-mutating status/identity sample; free-running samples are not atomic.',
    'get_cpu_registers':'Read registers from an already-held, unpaused instance; never establishes hold.',
    'get_screen_text':'Read CP437 text from an already-held text-mode guest.',
    'get_framebuffer':'Read a bounded native PNG from an already-held guest; latest rendered frame.',
    'read_memory':'Read a configured ordinary-RAM region. Obtain session/generation from status first.',
    'observe_machine':'Bracket registers plus optional text/frame/approved memory. Guest must already be held.'}


async def serve(adapter):
    # Optional dependency imported only when starting the MCP service.
    import anyio
    from mcp import types
    from mcp.server.lowlevel import Server
    from mcp.server.stdio import stdio_server

    async def list_tools(context, params):
        return types.ListToolsResult(tools=[types.Tool(name=name,
            description=DESCRIPTIONS[name],input_schema=SCHEMAS[name],
            annotations=types.ToolAnnotations(read_only_hint=True,destructive_hint=False,
                idempotent_hint=True,open_world_hint=False)) for name in TOOLS])

    async def call_tool(context, params):
        try:
            result, png = await anyio.to_thread.run_sync(adapter.call, params.name, params.arguments or {})
            content = [types.TextContent(type='text',text=json.dumps(result,ensure_ascii=True))]
            if png is not None:
                content.append(types.ImageContent(type='image',mime_type='image/png',
                    data=base64.b64encode(png).decode('ascii')))
            return types.CallToolResult(content=content,structured_content=result)
        except Refusal as exc:
            result = {'error':{'code':exc.code},
                      'server_session':getattr(exc, 'server_session', adapter.server_session),
                      'generation':getattr(exc, 'generation', 0)}
            if hasattr(exc, 'instance_id'):
                result['instance_id'] = exc.instance_id
            return types.CallToolResult(is_error=True,structured_content=result,
                content=[types.TextContent(type='text',text=json.dumps(result))])

    server = Server('deskmate-86box-readonly',version='0.1.0',
        instructions='Observation only. No hold, release, stepping, keyboard, reset or media operations. '
            'Coherent reads require an already-held guest; memory regions require owner approval.',
        on_list_tools=list_tools,on_call_tool=call_tool)
    try:
        async with stdio_server() as streams:
            await server.run(streams[0],streams[1],server.create_initialization_options())
    finally:
        adapter.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config',required=True)
    add_viewer_options(parser)
    args = parser.parse_args()
    try:
        import anyio
        adapter = Adapter(configuration(args.config))
        if adapter.registry is None:
            if args.journal is not None:
                parser.error('--journal requires an enabled observer in the MCP configuration')
            anyio.run(serve, adapter)
        else:
            from ..observer.http import ObserverServer

            with configured_feed(parser, args) as agent_feed, ObserverServer(
                adapter.registry, port=adapter.observer_port,
                agent_publication=agent_feed.publication if agent_feed else None,
                agent_page_limit=args.agent_page_limit,
            ) as observer:
                listener = Thread(target=observer.serve_forever, kwargs={'poll_interval': 0.1})
                listener.start()
                try:
                    print(f'86Box observatory: http://127.0.0.1:{observer.port}/',
                          file=sys.stderr, flush=True)
                    anyio.run(serve, adapter)
                finally:
                    observer.shutdown()
                    listener.join()
    except ImportError:
        print('86Box MCP: install the optional deskmate-formats[mcp] extra.',file=sys.stderr)
        raise SystemExit(2)
    except Exception:
        # Never include native errors, token contents, private paths or tracebacks.
        print('86Box MCP: STARTUP_OR_SERVER_FAILED; check private configuration and availability.',file=sys.stderr)
        raise SystemExit(2)


if __name__ == '__main__':
    main()
