package faraway;

import ctrmap.Workspace;
import ctrmap.tests.FrontierIsland;
import ctrmap.tests.FrontierPlaza;
import java.io.File;
import java.nio.file.Files;
import java.util.ArrayList;
import java.util.List;
import java.util.Properties;

/**
 * Frontier Island exterior (frontier/island_build.py, F11): Island GAME WORKSPACE PLAN. Runs after Build on the same
 * staged game. Plan keys:
 *   island.zone=209   island.grid=FILE (class rows, then height rows)   island.clerk=x,y,face
 *   island.building.N=name|doorX|doorY|zone|warp[|nopassengers]   (absolute map tiles; one door warp each, in N
 *   order; zone -1: no warp)
 * After the build every map-model texture is kept in the area's world pack and the load budget is printed
 * (FrontierPlaza.keepWorldTexturesInWorldPack, loadBudget; reports/frontier.md §23).
 */
public final class Island {

	private Island() {
	}

	public static void main(String[] a) throws Exception {
		Session.open(new File(a[0]), new File(a[1]));
		Properties plan = new Properties();
		try (java.io.Reader r = Files.newBufferedReader(new File(a[2]).toPath())) {
			plan.load(r);
		}
		int zone = Integer.parseInt(plan.getProperty("island.zone").trim());
		List<String> rows = Files.readAllLines(new File(plan.getProperty("island.grid").trim()).toPath());
		List<FrontierIsland.Building> buildings = new ArrayList<>();
		for (int i = 0; plan.getProperty("island.building." + i) != null; i++) {
			String[] b = plan.getProperty("island.building." + i).split("\\|");
			buildings.add(new FrontierIsland.Building(b[0], Integer.parseInt(b[1].trim()), Integer.parseInt(b[2].trim()),
					Integer.parseInt(b[3].trim()), Integer.parseInt(b[4].trim()),
					!(b.length > 5 && b[5].trim().equals("nopassengers"))));
		}
		String[] c = plan.getProperty("island.clerk").split(",");
		int[] clerk = {Integer.parseInt(c[0].trim()), Integer.parseInt(c[1].trim()), Integer.parseInt(c[2].trim())};
		System.out.println(FrontierIsland.build(zone, rows, buildings, clerk));
		System.out.println("pack " + Workspace.packArchives((p, what) -> { }));
		System.out.println(FrontierPlaza.keepWorldTexturesInWorldPack(zone));
		System.out.println("pack " + Workspace.packArchives((p, what) -> { }));
		System.out.println("outside the world pack: " + FrontierPlaza.worldTexturesOutsideWorldPack(zone));
		System.out.println(FrontierPlaza.loadBudget(zone));
	}
}
