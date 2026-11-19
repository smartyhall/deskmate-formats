# Observed DeskMate Draw interface

These observations are from original Draw 03.05.00 on the RSX VGA
profile. Interaction used keyboard scan codes and COM1 serial mouse
events on the authenticated emulator socket. Full native frames remain
in the private lab. The offline Workbench uses independent styling
and adapts native workflows to browser controls.

| Native surface | Observed behavior |
| --- | --- |
| Title strip | The session shows Help F1, date, drawing filename, and time across the top. It updates after Save As and after opening another FIG. |
| File F2 | New, Open, Save, Save As, Page Setup, Print, Exit, Run and About are visible in a populated drawing. The Save As dialog preselects the filename and updates the title after persistence. |
| Edit F3 | Clipboard, Select all, Move, Resize and corner commands depend on the selection. Ctrl+Insert copies and Shift+Insert pastes in the measured applications. |
| Actions F4 | Duplicate, Move to top, Move to bottom, Flip horizontal, Flip vertical, Rotate, Make object, Break object and Align appear in the selection-dependent menu. A valid group enabled Break object. PIPES did not enable it in the measured trial. |
| Zoom F5 | Normal, Two times, Four times, Half and Quarter. Normal and Two times were measured against world coordinates. |
| Options F6 | Patterns, Colors, Line, Brush, Text, Use keyboard, Use mouse and Scroll bars. The native Text dialog exposed outline and printer modes, face choices, point size, width, justification and style toggles. |
| Tools F7 | Select (Ctrl+S), Line (Ctrl+L), Rectangle (Ctrl+R), Ellipse (Ctrl+E), Text (Ctrl+T), Brush (Ctrl+B), Filled Brush, Arc (Ctrl+A), Polyline, Polygon (Ctrl+P). |

The menu band ends at framebuffer row 59, followed by the canvas
whose measured origin is `(0,62)`. The native Text options dialog
occupies approximately `[94,78,547,394]`. It uses a bordered title,
a font list, point/width fields, radio choices, checkboxes and
two bottom-right actions. Title, menu and modal colors depend on
native palette state. The mouse typically appears as an arrow until
the drawing tool presents a crosshair or text caret.

Reopening from DOS, parking the pointer in the title strip and
checking stable repaint clears tool and selection indicators for
comparison crops. Native selection shows rectangular handles around
the selected geometry. Keyboard mode uses arrows for placement and
Space to complete the measured drawing and editing gestures.
In a menu, a socket mouse action can highlight a command before
Enter executes it. That behavior mattered for Break object and
the native reflect control.

Browser keyboard shortcuts such as native Ctrl+S, Ctrl+A, Ctrl+L,
F3 and F5 conflict with commonly reserved browser commands. The
Workbench offers labeled commands, the O key for local opening,
and arrow panning after the viewport receives focus. Native creation
tools, original dialogs and a full keyboard-only drawing mode
remain interface research targets.
