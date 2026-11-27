// Bounded straight-line decode of explicitly requested file windows.
//
// Read-only: it follows no branch graph, runs no analysis and changes no
// program bytes, comments or symbols. Use it on a disposable project copy.
//
// Import the image itself with the standard MZ loader, or a stripped payload
// with BinaryLoader. When the imported program is a payload, pass
// --file-base 0x200 so reported FILE= values remain absolute offsets in the
// original executable.
//
// Example (headless):
//   analyzeHeadless PROJECT DIR -import PAYLOAD -processor "x86:LE:16:Real Mode" \
//     -loader BinaryLoader -loader-baseAddr 0x10000 -noanalysis -readOnly \
//     -scriptPath tools/ghidra -postScript BoundedDecode.java \
//     --windows 0xd7e5:0xd802 --file-base 0x200 --address-base 0x10000
import ghidra.app.script.GhidraScript;
import ghidra.app.util.PseudoDisassembler;
import ghidra.app.util.PseudoInstruction;
import ghidra.program.model.address.Address;

public class BoundedDecode extends GhidraScript {

    @Override
    public void run() throws Exception {
        String[] args = getScriptArgs();
        String windowsArg = null;
        long fileBase = 0;
        long addressBase = -1;

        for (int i = 0; i < args.length; i++) {
            switch (args[i]) {
                case "--windows" -> windowsArg = next(args, ++i, "--windows");
                case "--file-base" -> fileBase = Long.decode(next(args, ++i, "--file-base"));
                case "--address-base" -> addressBase = Long.decode(next(args, ++i, "--address-base"));
                default -> throw new IllegalArgumentException("unknown argument: " + args[i]);
            }
        }
        if (windowsArg == null) {
            throw new IllegalArgumentException("--windows START:END[,START:END] is required");
        }
        if (addressBase < 0) {
            // Default: the image starts at the lowest program address.
            addressBase = currentProgram.getMinAddress().getOffset();
        }

        PseudoDisassembler decoder = new PseudoDisassembler(currentProgram);
        println("PROGRAM=" + currentProgram.getName());
        println("LANGUAGE=" + currentProgram.getLanguageID());
        println("ADDRESS_BASE=0x" + Long.toHexString(addressBase));
        println("FILE_BASE=0x" + Long.toHexString(fileBase));

        for (String window : windowsArg.split(",")) {
            String[] parts = window.split(":");
            long start = Long.decode(parts[0]);
            long end = Long.decode(parts[1]);
            long file = start;
            int count = 0;
            println("WINDOW file=0x" + Long.toHexString(start)
                + "..0x" + Long.toHexString(end));
            while (file < end && count < 512) {
                long synthetic = addressBase + (file - fileBase);
                Address at = toAddr(synthetic);
                PseudoInstruction ins = decoder.disassemble(at);
                if (ins == null || ins.getLength() <= 0) {
                    println("FILE=" + Long.toHexString(file) + " UNDECODABLE");
                    break;
                }
                StringBuilder bytes = new StringBuilder();
                for (byte b : ins.getBytes()) {
                    bytes.append(String.format("%02x", b & 0xff));
                }
                println("FILE=" + Long.toHexString(file)
                    + " ADDR=" + at
                    + " BYTES=" + bytes
                    + " " + ins.toString());
                file += ins.getLength();
                count++;
            }
        }
    }

    private static String next(String[] args, int index, String flag) {
        if (index >= args.length) {
            throw new IllegalArgumentException(flag + " needs a value");
        }
        return args[index];
    }
}
