package ctrmap.tests;

import ctrmap.MapPainter;
import ctrmap.Workspace;
import ctrmap.formats.containers.GR;
import ctrmap.formats.tilemap.PaintedGeometry;
import ctrmap.formats.tilemap.TilePalette;
import ctrmap.gamedef.ArchiveType;
import java.util.ArrayList;
import java.util.List;

/**
 * Faraway Island: paints tall grass over the walkable tiles of a band of rows in a zone's own map cell, with the
 * map painter's COMPOSITE Apply (only those tiles are rebuilt; cliffs, water, collision and props elsewhere stay).
 * Lives in ctrmap.tests because it drives the painter with the same test seams TestWorldBuilder.paint uses.
 */
public final class FarawayGrass {

	private FarawayGrass() {
	}

	static final byte[] PAINTER_TALL_GRASS = {0x06, 0x00, 0x18, 0x3D};
	static final byte[] RETAIL_TALL_GRASS = {0x04, 0x40, 0x00, 0x20};

	static final ctrmap.humaninterface.SaveHistory OPS = new ctrmap.humaninterface.SaveHistory(
			() -> java.util.Collections.<Object>emptyList());

	/** Paints rows y0..y1 and returns the painter's report; the caller packs. */
	public static String paint(int zone, int y0, int y1) throws Exception {
		ctrmap.LoadedZone loaded = new ctrmap.LoadedZone();
		TestWindow.mZonePnl(new ctrmap.humaninterface.ZoneLoadingPanel(loaded, new ctrmap.humaninterface.tools.ToolSelection(),
				new RecordingEditors(), new ZoneEditorsSpy(), new RecordingNavi(), () -> { }, () -> { },
				UndoHistoryTest.overOneNumber(new int[]{0}), OPS));
		loaded.open(zone, new ctrmap.formats.zone.Zone(new ctrmap.formats.containers.ZO(Workspace.getWorkspaceFile(
				ArchiveType.ZONE_DATA, zone), Workspace.session()), Workspace.game()));
		int[] cell = MapPainter.firstRegionCell(loaded);
		if (cell == null) {
			throw new IllegalStateException("zone " + zone + " has no map cell");
		}
		int dim = MapPainter.DIM;
		TilePalette[][] grid = new TilePalette[dim][dim];
		MapPainter.loadFromRegion(cell[0], grid);
		byte[] tilemap = new GR(Workspace.getWorkspaceFile(ArchiveType.FIELD_DATA, cell[0]), Workspace.session()).getFile(0);
		int[][] height = new int[dim][dim];
		int[][] ramp = new int[dim][dim];
		boolean[][] touched = new boolean[dim][dim];
		int painted = 0;
		for (int y = 0; y < dim; y++) {
			java.util.Arrays.fill(ramp[y], PaintedGeometry.NO_RAMP);
			for (int x = 0; x < dim; x++) {
				int b0 = tilemap[4 + (y * dim + x) * 4] & 0xFF;
				// walkable tiles only: bit 0 of the first tuple byte marks a blocked tile
				if (y >= y0 && y <= y1 && (b0 & 1) == 0) {
					grid[y][x] = TilePalette.TALL_GRASS;
					touched[y][x] = true;
					painted++;
				}
			}
		}
		System.out.println("region " + cell[0] + ": " + painted + " tiles of rows " + y0 + "-" + y1 + " -> tall grass");
		Host host = new Host();
		String report = MapPainter.applyToZone(loaded, zone, grid, height, ramp,
				ctrmap.formats.tilemap.TerrainLighting.daytime(), true, new ArrayList<MapPainter.Placed>(), touched, host);
		if (!host.errors.isEmpty()) {
			throw new IllegalStateException("the Apply reported errors: " + host.errors);
		}
		// The painter's TALL_GRASS tuple (06 00 18 3D) is not ORAS tall grass: across the 857 retail regions it
		// shares the water prefix and the player cannot step on it. Retail tall grass, measured on Route 102
		// (zone 24, the tiles around 125,133) and present in 59 regions, is 04 40 00 20.
		int region = MapPainter.firstRegionCell(loaded)[0];
		GR gr = new GR(Workspace.getWorkspaceFile(ArchiveType.FIELD_DATA, region), Workspace.session());
		byte[] out = gr.getFile(0).clone();
		int fixed = 0;
		for (int y = 0; y < dim; y++) {
			for (int x = 0; x < dim; x++) {
				if (touched[y][x]) {
					int off = 4 + (y * dim + x) * 4;
					if (out[off] != PAINTER_TALL_GRASS[0] || out[off + 1] != PAINTER_TALL_GRASS[1]
							|| out[off + 2] != PAINTER_TALL_GRASS[2] || out[off + 3] != PAINTER_TALL_GRASS[3]) {
						throw new IllegalStateException("tile " + x + "," + y + " of region " + region + " is not the painter's tall grass");
					}
					System.arraycopy(RETAIL_TALL_GRASS, 0, out, off, 4);
					fixed++;
				}
			}
		}
		gr.storeFile(0, out);
		System.out.println("region " + region + ": " + fixed + " tiles set to retail tall grass 04400020");
		return report + (host.said.isEmpty() ? "" : "\n" + String.join("\n", host.said));
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
