import ghidra.app.script.GhidraScript;
import ghidra.app.util.PseudoDisassembler;
import ghidra.app.util.PseudoInstruction;
import ghidra.program.model.address.Address;

/** Bounded straight-line decode, no analysis or program mutation.
 * Import the original DESK.EXE MZ payload (file 0x200 onward) as
 * x86:LE:16:Real Mode at synthetic 1000:0000. Output stays private.
 * Synthetic addresses are not guest addresses; relocations are checked separately.
 */
public class CalendarBinding25 extends GhidraScript {
    public void run() throws Exception {
        int[][] windows = {
            {0x37a9, 0x37ee}, {0x4260, 0x4296}, {0x429f, 0x42a1},
            {0x42ba, 0x432d},
            {0x5c2, 0x5f0}, {0x618, 0x61e}, {0x65f, 0x686},
            {0x705, 0x713}, {0x2d65, 0x2dce}, {0x2c61, 0x2c8a}
        };
        PseudoDisassembler decoder = new PseudoDisassembler(currentProgram);
        for (int[] window : windows) {
            int file = window[0];
            for (int n = 0; n < 100 && file < window[1]; n++) {
                Address at = currentProgram.getAddressFactory()
                    .getDefaultAddressSpace().getAddress(0x10000L + file - 0x200);
                PseudoInstruction ins = decoder.disassemble(at);
                if (ins == null || ins.getLength() <= 0) {
                    throw new IllegalStateException("Undecodable file " + Integer.toHexString(file));
                }
                StringBuilder bytes = new StringBuilder();
                for (byte b : ins.getBytes()) bytes.append(String.format("%02x", b & 255));
                println("FILE=" + Integer.toHexString(file) + " BYTES=" + bytes + " " + ins);
                file += ins.getLength();
            }
        }
    }
}
