package faraway;

import ctrmap.Workspace;
import ctrmap.tests.FrontierPlaza;
import java.io.File;
import java.nio.file.Files;
import java.util.ArrayList;
import java.util.List;
import java.util.Properties;

/**
 * Frontier Island plaza (frontier/island_build.py): Plaza GAME WORKSPACE PLAN. Runs after Build on the same staged
 * game. The plan names the zone, the painted rectangle, the buildings and which doors lead where:
 *   plaza.zone=209   plaza.rect=x0,y0,x1,y1   plaza.building.N=name|x|y[|nodoorprop,nopassengers]   plaza.door.N=zone,warp
 *   plaza.heightof=W (the zone's warp whose height the door warps take; all old warps are replaced)
 */
public final class Plaza {

	private Plaza() {
	}

	public static void main(String[] a) throws Exception {
		Session.open(new File(a[0]), new File(a[1]));
		Properties plan = new Properties();
		try (java.io.Reader r = Files.newBufferedReader(new File(a[2]).toPath())) {
			plan.load(r);
		}
		int zone = Integer.parseInt(plan.getProperty("plaza.zone").trim());
		String[] rect = plan.getProperty("plaza.rect").split(",");
		List<FrontierPlaza.Spot> spots = new ArrayList<>();
		List<FrontierPlaza.Spot> doors = new ArrayList<>();
		List<int[]> targets = new ArrayList<>();
		for (int i = 0; plan.getProperty("plaza.building." + i) != null; i++) {
			String[] b = plan.getProperty("plaza.building." + i).split("\\|");
			java.util.List<String> flags = java.util.Arrays.asList(b.length > 3 ? b[3].trim().split(",") : new String[0]);
			for (String f : flags) {
				if (!f.equals("nodoorprop") && !f.equals("nopassengers")) {
					throw new IllegalArgumentException("plaza.building." + i + ": unknown flag " + f);
				}
			}
			FrontierPlaza.Spot s = new FrontierPlaza.Spot(b[0], Integer.parseInt(b[1].trim()), Integer.parseInt(b[2].trim()),
					!flags.contains("nodoorprop"), !flags.contains("nopassengers"));
			spots.add(s);
			String door = plan.getProperty("plaza.door." + i);
			if (door != null) {
				String[] t = door.split(",");
				doors.add(s);
				targets.add(new int[]{Integer.parseInt(t[0].trim()), Integer.parseInt(t[1].trim())});
			}
		}
		String report = FrontierPlaza.paint(zone, Integer.parseInt(rect[0].trim()), Integer.parseInt(rect[1].trim()),
				Integer.parseInt(rect[2].trim()), Integer.parseInt(rect[3].trim()), spots);
		System.out.println("apply: " + report.replace("\n", " | "));
		System.out.println("pack " + Workspace.packArchives((p, what) -> { }));
		System.out.println(FrontierPlaza.linkDoors(zone, Integer.parseInt(plan.getProperty("plaza.heightof").trim()), doors, targets));
		System.out.println("pack " + Workspace.packArchives((p, what) -> { }));
	}
}
