package ctrmap;

/**
 * Frontier Island (frontier/island_build.py, ctrmap.tests.FrontierIsland): reach for the painter's staged-area commit,
 * which is package-private. The island stages its door-prop registrations, texture carries and world textures into
 * one {@link MapPainter.StagedArea} exactly as MapPainter.applyToZone does, then writes them with this.
 */
public final class IslandArea {

	private IslandArea() {
	}

	public static void commit(MapPainter.StagedArea area) {
		area.commit();
	}
}
