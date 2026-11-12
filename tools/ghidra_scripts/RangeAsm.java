// Disassembles (on the fly) and prints the instructions in [startRva, endRva), following code the analysis missed.
// Args: startRva endRva   Output: "ASM <rva>: <instr>"
//@category modkit
import ghidra.app.script.GhidraScript;
import ghidra.program.model.address.Address;
import ghidra.program.model.listing.Instruction;

public class RangeAsm extends GhidraScript {
    @Override
    protected void run() throws Exception {
        String[] a = getScriptArgs();
        long base = currentProgram.getImageBase().getOffset();
        Address s = toAddr(base + Long.decode(a[0])), e = toAddr(base + Long.decode(a[1]));
        disassemble(s);
        Instruction i = getInstructionAt(s);
        while (i != null && i.getAddress().compareTo(e) < 0) {
            println(String.format("ASM 0x%x: %s", i.getAddress().getOffset() - base, i));
            Instruction n = i.getNext();
            if (n == null || !n.getAddress().equals(i.getMaxAddress().add(1))) {
                Address nx = i.getMaxAddress().add(1);
                disassemble(nx);
                n = getInstructionAt(nx);
            }
            i = n;
        }
    }
}
