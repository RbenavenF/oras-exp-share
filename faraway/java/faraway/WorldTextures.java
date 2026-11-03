package faraway;

import ctrmap.tests.FrontierPlaza;
import java.io.File;

/**
 * Read-only survey (reports/frontier.md §23): WorldTextures GAME WORKSPACE ZONE prints the textures the zone's map
 * models draw with that its area's world pack lacks, whether the prop pack holds each, and the load budget.
 */
public final class WorldTextures {

	private WorldTextures() {
	}

	public static void main(String[] a) throws Exception {
		Session.open(new File(a[0]), new File(a[1]));
		System.out.println("outside the world pack: " + FrontierPlaza.worldTexturesOutsideWorldPack(Integer.parseInt(a[2])));
		System.out.println(FrontierPlaza.loadBudget(Integer.parseInt(a[2])));
	}
}
