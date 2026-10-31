// Decompile functions containing the supplied hex addresses into local text files.
//@category ORAS
import ghidra.app.script.GhidraScript;
import ghidra.app.decompiler.DecompInterface;
import ghidra.app.decompiler.DecompileResults;
import ghidra.program.model.address.Address;
import ghidra.program.model.listing.Function;
import java.nio.file.Files;
import java.nio.file.Path;

public class DumpFunctions extends GhidraScript {
    public void run() throws Exception {
        String[] args = getScriptArgs();
        Path output = Path.of(args[0]);
        Files.createDirectories(output);
        DecompInterface decompiler = new DecompInterface();
        try {
            decompiler.openProgram(currentProgram);
            for (int i = 1; i < args.length; i++) {
                Address address = toAddr(Long.parseUnsignedLong(args[i].replace("0x", ""), 16));
                Function function = getFunctionContaining(address);
                if (function == null) {
                    disassemble(address);
                    function = createFunction(address, null);
                }
                if (function == null) {
                    println("No function at " + address);
                    continue;
                }
                DecompileResults result = decompiler.decompileFunction(function, 45, monitor);
                String text = result.decompileCompleted() ? result.getDecompiledFunction().getC() : result.getErrorMessage();
                Files.writeString(output.resolve(function.getEntryPoint() + ".c"), text);
                println("Dumped " + function.getEntryPoint());
            }
        } finally {
            decompiler.dispose();
        }
    }
}
