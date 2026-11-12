// Functions whose entry lies in [lo, hi) (RVAs), with their callers' function entries.
// Args: lo hi (RVAs)   Output: "FN <rva> <name> size <n> callers <rva,...>"
//@category modkit
import ghidra.app.script.GhidraScript;
import ghidra.program.model.listing.Function;
import ghidra.program.model.symbol.Reference;
import java.util.TreeSet;

public class FuncsInRange extends GhidraScript {
    @Override
    protected void run() throws Exception {
        String[] a = getScriptArgs();
        long base = currentProgram.getImageBase().getOffset();
        long lo = Long.decode(a[0]), hi = Long.decode(a[1]);
        for (Function f : currentProgram.getFunctionManager().getFunctions(toAddr(base + lo), true)) {
            long e = f.getEntryPoint().getOffset() - base;
            if (e >= hi) break;
            TreeSet<String> callers = new TreeSet<>();
            for (Reference r : getReferencesTo(f.getEntryPoint())) {
                Function c = getFunctionContaining(r.getFromAddress());
                callers.add(c == null ? "-" : String.format("0x%x", c.getEntryPoint().getOffset() - base));
            }
            println(String.format("FN 0x%x %s size %d callers %s", e, f.getName(), f.getBody().getNumAddresses(),
                    String.join(",", callers)));
        }
    }
}
