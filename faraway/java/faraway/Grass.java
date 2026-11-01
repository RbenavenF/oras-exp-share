package faraway;

import ctrmap.Workspace;
import java.io.File;

/**
 * Tall grass for the Faraway Island meadow: Grass GAME WORKSPACE ZONE FIRST_ROW LAST_ROW.
 * Runs after Build on the same staged game; paints the walkable tiles of the rows and packs.
 */
public final class Grass {

	private Grass() {
	}

	public static void main(String[] a) throws Exception {
		Session.open(new File(a[0]), new File(a[1]));
		String report = ctrmap.tests.FarawayGrass.paint(Integer.parseInt(a[2]), Integer.parseInt(a[3]), Integer.parseInt(a[4]));
		System.out.println("apply: " + report.replace("\n", " | "));
		System.out.println("pack " + Workspace.packArchives((p, what) -> { }));
	}
}
