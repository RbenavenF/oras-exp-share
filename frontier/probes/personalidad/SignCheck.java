package faraway;
import ctrmap.Workspace;
import ctrmap.ZoneTables;
import ctrmap.formats.containers.ContainerBytes;
import java.io.File;
public final class SignCheck {
	public static void main(String[] a) throws Exception {
		Session.open(new File(a[0]), new File(a[1]));
		for (int i = 2; i < a.length; i++) {
			int z = Integer.parseInt(a[i]);
			byte[] zo = ZoneTables.zoneNow(Workspace.session(), z);
			ctrmap.formats.scripts.GFLPawnScript s = new ctrmap.formats.scripts.GFLPawnScript(ContainerBytes.subfile(zo, 2));
			s.decompressThis();
			System.out.println("zone " + z + " sign wrapper: " + (ctrmap.formats.scripts.ZoneScriptAnalyzer.findSignWrapper(s) != null));
		}
	}
}
