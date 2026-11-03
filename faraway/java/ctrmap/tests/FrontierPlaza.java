package ctrmap.tests;

import ctrmap.MapPainter;
import ctrmap.Workspace;
import ctrmap.formats.tilemap.PaintedGeometry;
import ctrmap.formats.tilemap.TilePalette;
import ctrmap.formats.zone.WorldGrid;
import ctrmap.formats.zone.ZoneEntities;
import ctrmap.gamedef.ArchiveType;
import java.util.ArrayList;
import java.util.List;

/**
 * Frontier Island plaza: paints a path rectangle over the zone's own map cell with the map painter's COMPOSITE
 * Apply (tiles outside the rectangle keep the donor's sea and pier) and stamps catalogue buildings on it. No door
 * is wired by the painter (DoorWiring.SKIP): every building is a mock except the one door {@link #linkDoor} gives
 * a warp. Lives in ctrmap.tests because it drives the painter through the same seams as TestWorldBuilder.paint.
 */
public final class FrontierPlaza {

	private FrontierPlaza() {
	}

	static final ctrmap.humaninterface.SaveHistory OPS = new ctrmap.humaninterface.SaveHistory(
			() -> java.util.Collections.<Object>emptyList());

	/** One building: catalogue name and anchor (top-left tile of its box, cell-local). */
	public static final class Spot {

		public final String name;
		public final int tx, ty;
		/** False stamps the building without its swinging-door prop. */
		public final boolean doorProp;
		/** False leaves the cut's passengers (shadow decals, terrain chips, sea planes) behind. */
		public final boolean passengers;

		public Spot(String name, int tx, int ty, boolean doorProp, boolean passengers) {
			this.name = name;
			this.tx = tx;
			this.ty = ty;
			this.doorProp = doorProp;
			this.passengers = passengers;
		}
	}

	static ctrmap.LoadedZone open(int zone) throws Exception {
		ctrmap.LoadedZone loaded = new ctrmap.LoadedZone();
		TestWindow.mZonePnl(new ctrmap.humaninterface.ZoneLoadingPanel(loaded, new ctrmap.humaninterface.tools.ToolSelection(),
				new RecordingEditors(), new ZoneEditorsSpy(), new RecordingNavi(), () -> { }, () -> { },
				UndoHistoryTest.overOneNumber(new int[]{0}), OPS));
		loaded.open(zone, new ctrmap.formats.zone.Zone(new ctrmap.formats.containers.ZO(Workspace.getWorkspaceFile(
				ArchiveType.ZONE_DATA, zone), Workspace.session()), Workspace.game()));
		return loaded;
	}

	public static ctrmap.formats.h3d.BuildingCatalog.Entry entry(String name) {
		ctrmap.formats.h3d.BuildingCatalog.Entry found = null;
		for (ctrmap.formats.h3d.BuildingCatalog.Entry e : ctrmap.formats.h3d.BuildingCatalog.entries()) {
			if (name.equals(e.name)) {
				if (found != null) {
					throw new IllegalStateException("the building catalogue has two entries named " + name);
				}
				found = e;
			}
		}
		if (found == null) {
			throw new IllegalStateException("the building catalogue has no entry named " + name);
		}
		return found;
	}

	/** A copy of the entry whose door prop is "-" (the painter places none for it). */
	static ctrmap.formats.h3d.BuildingCatalog.Entry withoutDoorProp(ctrmap.formats.h3d.BuildingCatalog.Entry e) {
		ctrmap.formats.h3d.BuildingCatalog.Entry c = new ctrmap.formats.h3d.BuildingCatalog.Entry();
		for (java.lang.reflect.Field f : c.getClass().getFields()) {
			try {
				f.set(c, f.get(e));
			} catch (IllegalAccessException ex) {
				throw new IllegalStateException(ex);
			}
		}
		c.doorProp = "-";
		return c;
	}

	/**
	 * Paints cell-local tiles x0..x1, y0..y1 as path and stamps the buildings; returns the painter's report. The
	 * caller packs. Refuses a building outside the rectangle or overlapping another.
	 */
	public static String paint(int zone, int x0, int y0, int x1, int y1, List<Spot> spots) throws Exception {
		ctrmap.LoadedZone loaded = open(zone);
		if (ctrmap.formats.propdata.PropDatabase.get(Workspace.session()) == null) {
			throw new IllegalStateException("the prop database did not build, and the painter places door props from it");
		}
		int[] cell = MapPainter.firstRegionCell(loaded);
		if (cell == null) {
			throw new IllegalStateException("zone " + zone + " has no map cell");
		}
		int dim = MapPainter.DIM;
		TilePalette[][] grid = new TilePalette[dim][dim];
		MapPainter.loadFromRegion(cell[0], grid);
		int[][] height = new int[dim][dim];
		int[][] ramp = new int[dim][dim];
		boolean[][] touched = new boolean[dim][dim];
		for (int y = 0; y < dim; y++) {
			java.util.Arrays.fill(ramp[y], PaintedGeometry.NO_RAMP);
		}
		for (int y = y0; y <= y1; y++) {
			for (int x = x0; x <= x1; x++) {
				grid[y][x] = TilePalette.PATH;
				touched[y][x] = true;
			}
		}
		List<MapPainter.Placed> placed = new ArrayList<>();
		for (Spot s : spots) {
			MapPainter.Placed p = new MapPainter.Placed(s.doorProp ? entry(s.name) : withoutDoorProp(entry(s.name)), s.tx, s.ty,
					s.passengers);
			if (s.tx < x0 || s.ty < y0 || s.tx + p.e.tilesW() - 1 > x1 || s.ty + p.e.tilesH() - 1 > y1) {
				throw new IllegalStateException(s.name + " at " + s.tx + "," + s.ty + " leaves the painted rectangle");
			}
			for (MapPainter.Placed q : placed) {
				for (int y = s.ty; y < s.ty + p.e.tilesH(); y++) {
					for (int x = s.tx; x < s.tx + p.e.tilesW(); x++) {
						if (q.contains(x, y)) {
							throw new IllegalStateException(s.name + " overlaps " + q.e.name + " at " + x + "," + y);
						}
					}
				}
			}
			placed.add(p);
			System.out.println("place " + p.e.kind + " \"" + p.e.name + "\" " + p.e.tilesW() + "x" + p.e.tilesH() + " at "
					+ s.tx + "," + s.ty + (p.e.enterable() ? " door " + (s.tx + p.e.doorDX) + "," + (s.ty + p.e.doorDY) : "") + " door prop " + p.e.doorProp + (s.passengers ? "" : ", no passengers"));
		}
		System.out.println("region " + cell[0] + " (cell " + cell[1] + "," + cell[2] + "): path " + x0 + "," + y0 + "-" + x1 + "," + y1);
		Host host = new Host();
		String report = MapPainter.applyToZone(loaded, zone, grid, height, ramp,
				ctrmap.formats.tilemap.TerrainLighting.daytime(), true, placed, touched, host);
		if (!host.errors.isEmpty()) {
			throw new IllegalStateException("the Apply reported errors: " + host.errors);
		}
		return report + (host.said.isEmpty() ? "" : "\n" + String.join("\n", host.said));
	}

	/**
	 * Replaces the zone's warps with one door warp per (spot, target): on the spot's door tile, at the height of
	 * the zone's old warp `heightOf` (the painted floor lies at the donor ground the pier stands on), facing north,
	 * with the door transition retail doors use (MapPainter.wireDoorWarps). Returns the new warp list's summary.
	 */
	public static String linkDoors(int zone, int heightOf, List<Spot> spots, List<int[]> targets) throws Exception {
		ctrmap.LoadedZone loaded = open(zone);
		int[] cell = MapPainter.firstRegionCell(loaded);
		ctrmap.formats.containers.ZO zo = new ctrmap.formats.containers.ZO(Workspace.getWorkspaceFile(ArchiveType.ZONE_DATA, zone),
				Workspace.session());
		ZoneEntities ent = new ZoneEntities(zo.getFile(1));
		int z = ent.warps.get(heightOf).z;
		ent.warps.clear();
		StringBuilder out = new StringBuilder();
		for (int i = 0; i < spots.size(); i++) {
			Spot s = spots.get(i);
			ctrmap.formats.h3d.BuildingCatalog.Entry e = entry(s.name);
			if (!e.enterable()) {
				throw new IllegalStateException(s.name + " has no door");
			}
			ZoneEntities.Warp w = new ZoneEntities.Warp();
			w.targetZone = targets.get(i)[0];
			w.targetWarpId = targets.get(i)[1];
			w.faceDirection = 1;
			w.transitionType = 3;
			w.coordinateType = 0;
			w.x = WorldGrid.tileCentre(cell[1] * 40 + s.tx + e.doorDX);
			w.y = WorldGrid.tileCentre(cell[2] * 40 + s.ty + e.doorDY);
			w.z = z;
			w.w = 1;
			w.h = 1;
			ent.warps.add(w);
			out.append("warp ").append(ent.warps.size() - 1).append(" door of ").append(s.name).append(" at tile ")
					.append(cell[1] * 40 + s.tx + e.doorDX).append(",").append(cell[2] * 40 + s.ty + e.doorDY)
					.append(" z ").append(z).append(" -> zone ").append(w.targetZone).append(" warp ").append(w.targetWarpId).append("\n");
		}
		ent.modified = true;
		zo.storeFile(1, ent.assembleData());
		return out.toString().trim();
	}

	static final class Host implements MapPainter.Host {

		final List<String> said = new ArrayList<>();
		final List<String> errors = new ArrayList<>();

		@Override
		public ctrmap.AreaForker.ForkResult ownArea(ctrmap.LoadedZone loaded, int zoneIndex, String why) {
			List<String> asked = ctrmap.Ui.record("Give this zone its own area");
			try {
				return ctrmap.humaninterface.AreaForkPrompt.ensurePrivate(loaded, null, zoneIndex, why, OPS, () -> { });
			} finally {
				ctrmap.Ui.stopRecording();
				said.addAll(asked);
			}
		}

		@Override
		public MapPainter.DoorWiring doorWiring(int enterable) {
			return MapPainter.DoorWiring.SKIP;
		}

		@Override
		public boolean transplantSignRoutine(int instructions) {
			return false;
		}

		@Override
		public MapPainter.SignText signText(MapPainter.Placed sign) {
			return null;
		}

		@Override
		public void tell(String text, String title) {
			said.add(title + ": " + text.replace("\n", " | "));
		}

		@Override
		public void error(String text, String title) {
			errors.add(title + ": " + text);
		}

		@Override
		public void slotTaken(int slot) {
			said.add("slot taken: " + slot);
		}

		@Override
		public void pack(int zoneIndex, String report) {
			// the caller packs once, after the Apply
		}
	}
}
