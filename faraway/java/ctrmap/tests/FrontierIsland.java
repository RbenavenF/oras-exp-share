package ctrmap.tests;

import ctrmap.GeometryForker;
import ctrmap.MapPainter;
import ctrmap.Workspace;
import ctrmap.formats.containers.AD;
import ctrmap.formats.containers.GR;
import ctrmap.formats.containers.MM;
import ctrmap.formats.containers.ZO;
import ctrmap.formats.h3d.BchTexturePack;
import ctrmap.formats.h3d.BuildingCatalog;
import ctrmap.formats.h3d.RegionFactory;
import ctrmap.formats.mapmatrix.MapMatrix;
import ctrmap.formats.tilemap.PaintedGeometry;
import ctrmap.formats.tilemap.PaintedRegionBuilder;
import ctrmap.formats.tilemap.TerrainLighting;
import ctrmap.formats.tilemap.TilePalette;
import ctrmap.formats.zone.WorldGrid;
import ctrmap.formats.zone.ZoneEntities;
import ctrmap.formats.zone.ZoneHeader;
import ctrmap.gamedef.ArchiveType;
import java.io.File;
import java.nio.file.Files;
import java.nio.file.StandardCopyOption;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;

/**
 * Frontier Island exterior (F11-ISLA-CONSTRUCCION, frontier/island_build.py, reports/diseno/isla-esmeralda.md): the
 * zone's private map becomes CELLS_X x CELLS_Y painted cells of 40x40 tiles from a class grid and a height grid (the
 * Emerald trace of frontier/island_layout.py at its OFFSET), each region a copy of the retail GR container of region
 * 489 (seven subfiles) with its row and column in GR[4][0..1] (F11-ISLA-TRAZADO: all-zero coordinates froze walking
 * and left cells undrawn). Catalogue buildings are stamped into the cell that holds them, each planted at its door
 * tile's height; their swinging-door props go into that cell's GR[3] at absolute coordinates. One door warp per
 * building replaces the zone's warps, and the ferry clerk (NPC 0) moves to the pier. Brush and building textures go
 * into the area's world pack (§23: map models read the world pack only).
 */
public final class FrontierIsland {

	public static final int CELLS_X = 4, CELLS_Y = 2, DIM = 40;
	/** The retail region whose GR container the cells copy (Battle Resort, ORAS). */
	public static final int CONTAINER_REGION = 489;

	private FrontierIsland() {
	}

	/** One building: catalogue name and its door tile (absolute map tile). */
	public static final class Building {

		public final String name;
		public final int doorX, doorY;
		public final int targetZone, targetWarp;
		/** False leaves the cut's passengers (shadow decals, terrain chips, sea planes) behind. */
		public final boolean passengers;

		public Building(String name, int doorX, int doorY, int targetZone, int targetWarp, boolean passengers) {
			this.name = name;
			this.passengers = passengers;
			this.doorX = doorX;
			this.doorY = doorY;
			this.targetZone = targetZone;
			this.targetWarp = targetWarp;
		}
	}

	/** Grid classes (frontier/island_layout.py LEGEND) to painter brushes; anything else is path. */
	static TilePalette brush(char c) {
		switch (c) {
			case '~':
			case 'w':
				return TilePalette.WATER;
			case ',':
			case 'T':
			case 'p':
				return TilePalette.GRASS;
			case 's':
				return TilePalette.SAND;
			case '=':
				return TilePalette.STAIRS_Z;
			case '#':
			case 'o':
			case 'f':
			case 'x':
			case 'B':
				return TilePalette.ROCK;
			default:
				return TilePalette.PATH;
		}
	}

	/**
	 * Builds the island. `rows`: CELLS_Y*40 class rows then as many height rows (digits, levels of
	 * PaintedGeometry.STEP). `clerk`: x, y, face of NPC 0. Returns the report; the caller packs.
	 */
	public static String build(int zone, List<String> rows, List<Building> buildings, int[] clerk) throws Exception {
		int w = CELLS_X * DIM, h = CELLS_Y * DIM;
		if (rows.size() != 2 * h) {
			throw new IllegalArgumentException(h + " class rows and " + h + " height rows required, got " + rows.size());
		}
		for (String r : rows) {
			if (r.length() != w) {
				throw new IllegalArgumentException("every grid row must have " + w + " tiles: " + r);
			}
		}
		if (ctrmap.formats.propdata.PropDatabase.get(Workspace.session()) == null) {
			throw new IllegalStateException("the prop database did not build, and the door props come from it");
		}
		if (ctrmap.AreaForker.areaSharers(zone) > 0) {
			throw new IllegalStateException("zone " + zone + " must have its own area");
		}
		ctrmap.LoadedZone loaded = FrontierPlaza.open(zone);
		int area = ctrmap.AreaForker.currentArea(zone);
		StringBuilder out = new StringBuilder();
		ZO zo = new ZO(Workspace.getWorkspaceFile(ArchiveType.ZONE_DATA, zone), Workspace.session());
		ZoneHeader hdr = new ZoneHeader(zo.getFile(0), ctrmap.gamedef.GameType.ORAS);
		MM mm = new MM(Workspace.getWorkspaceFile(ArchiveType.MAP_MATRIX, hdr.mapmatrixID), Workspace.session());
		MapMatrix matrix = new MapMatrix(mm, CELLS_X, CELLS_Y, 0);
		matrix.cambounds.get(0).east = w * 18;
		matrix.cambounds.get(0).south = h * 18;

		// Each building's anchor and the height it stands at; refuse one that leaves its cell or overlaps another.
		Map<Building, MapPainter.Placed> placed = new LinkedHashMap<>();
		for (Building b : buildings) {
			BuildingCatalog.Entry e = FrontierPlaza.entry(b.name);
			if (!e.enterable()) {
				throw new IllegalStateException(b.name + " has no door");
			}
			int ax = b.doorX - e.doorDX, ay = b.doorY - e.doorDY;
			int cx = ax / DIM, cy = ay / DIM;
			if (ax < 0 || ay < 0 || (ax + e.tilesW() - 1) / DIM != cx || (ay + e.tilesH() - 1) / DIM != cy || cy >= CELLS_Y) {
				throw new IllegalStateException(b.name + " at " + ax + "," + ay + " (" + e.tilesW() + "x" + e.tilesH()
						+ ") does not lie inside one map cell");
			}
			for (Map.Entry<Building, MapPainter.Placed> q : placed.entrySet()) {
				MapPainter.Placed p = q.getValue();
				int qx = q.getKey().doorX - p.e.doorDX, qy = q.getKey().doorY - p.e.doorDY;
				if (ax < qx + p.e.tilesW() && qx < ax + e.tilesW() && ay < qy + p.e.tilesH() && qy < ay + e.tilesH()) {
					throw new IllegalStateException(b.name + " overlaps " + p.e.name);
				}
			}
			placed.put(b, new MapPainter.Placed(e, ax - cx * DIM, ay - cy * DIM, b.passengers));
		}

		int first = GeometryForker.nextFreeRegion(Workspace.session(), Workspace.getArchive(ArchiveType.FIELD_DATA));
		GR container = BuildingCatalog.pristineRegion(Workspace.session(), CONTAINER_REGION);
		byte[] donor = container.getFile(1);
		Map<Integer, Set<String>> brushNeeds = new LinkedHashMap<>();
		Map<Integer, Set<String>> stampNeeds = new LinkedHashMap<>();
		MapPainter.StagedArea staged = new MapPainter.StagedArea(loaded, area, zone);
		StringBuilder propNote = new StringBuilder();
		Map<String, Integer> propUid = new LinkedHashMap<>();
		for (MapPainter.Placed p : placed.values()) {
			if (p.e.doorProp != null && !p.e.doorProp.equals("-") && !propUid.containsKey(p.e.doorProp)) {
				propUid.put(p.e.doorProp, MapPainter.ensureDoorPropRegistered(p.e.doorProp, staged, propNote));
			}
		}
		for (int cy = 0; cy < CELLS_Y; cy++) {
			for (int cx = 0; cx < CELLS_X; cx++) {
				TilePalette[][] grid = new TilePalette[DIM][DIM];
				int[][] height = new int[DIM][DIM], ramp = new int[DIM][DIM];
				float[][] floorY = new float[DIM][DIM];
				for (int y = 0; y < DIM; y++) {
					for (int x = 0; x < DIM; x++) {
						int gx = cx * DIM + x, gy = cy * DIM + y;
						grid[y][x] = brush(rows.get(gy).charAt(gx));
						height[y][x] = rows.get(h + gy).charAt(gx) - '0';
						ramp[y][x] = PaintedGeometry.NO_RAMP;
						floorY[y][x] = height[y][x] * PaintedGeometry.STEP;
					}
				}
				byte[] template = MapPainter.importBrushMaterials(donor, grid, null, brushNeeds);
				RegionFactory.BlankContent bc = PaintedRegionBuilder.build(Workspace.session(), template, grid, height, ramp,
						TerrainLighting.daytime(), false);
				// Stairs keep their slope but walk as ground: the catalogue's 0x6c behaviour would not let the player
				// climb the reception step (F11-ISLA-TRAZADO prototype).
				for (int y = 0; y < DIM; y++) {
					for (int x = 0; x < DIM; x++) {
						if (grid[y][x] == TilePalette.STAIRS_Z) {
							bc.tilemap[4 + (y * DIM + x) * 4 + 3] = 0;
						}
					}
				}
				// one quad per run of identical flat tiles, before any building is stamped (IslandFloors: lossless)
				StringBuilder merged = new StringBuilder();
				int before = bc.model.length;
				bc.model = IslandFloors.compact(bc.model, merged);
				List<MapPainter.Placed> here = new ArrayList<>();
				ctrmap.formats.propdata.GRPropData doors = new ctrmap.formats.propdata.GRPropData();
				for (Map.Entry<Building, MapPainter.Placed> q : placed.entrySet()) {
					Building b = q.getKey();
					MapPainter.Placed p = q.getValue();
					if (b.doorX / DIM != cx || b.doorY / DIM != cy) {
						continue;
					}
					// planted at the door tile's height (stampPlaced reads the anchor tile's floor)
					floorY[p.ty][p.tx] = height[b.doorY - cy * DIM][b.doorX - cx * DIM] * PaintedGeometry.STEP;
					here.add(p);
					if (propUid.containsKey(p.e.doorProp)) {
						ctrmap.formats.propdata.GRProp prop = new ctrmap.formats.propdata.GRProp();
						prop.uid = propUid.get(p.e.doorProp);
						prop.x = WorldGrid.tileCentre(b.doorX);
						prop.z = WorldGrid.tileCentre(b.doorY);
						prop.y = floorY[p.ty][p.tx];
						doors.props.add(prop);
					}
				}
				String note = "";
				for (MapPainter.Placed p : here) {
					List<MapPainter.Placed> one = new ArrayList<>();
					one.add(p);
					note += MapPainter.stampPlaced(bc, one, height, floorY, stampNeeds).replace("\n", " ") + " ";
				}
				int region = first + cy * CELLS_X + cx;
				File f = new File(Workspace.getExtractionDirectory(ArchiveType.FIELD_DATA), String.valueOf(region));
				Files.copy(container.getOriginFile().toPath(), f.toPath(), StandardCopyOption.REPLACE_EXISTING);
				GR gr = new GR(f, Workspace.session());
				gr.storeFile(0, bc.tilemap);
				gr.storeFile(1, bc.model);
				gr.storeFile(2, bc.collision);
				gr.storeFile(3, doors.props.isEmpty() ? bc.props : doors.assemblePropData());
				byte[] extended = gr.getFile(4).clone();
				extended[0] = (byte) cy;
				extended[1] = (byte) cx;
				gr.storeFile(4, extended);
				Workspace.session().registerPendingCompression(ArchiveType.FIELD_DATA, region, true);
				matrix.ids.set(cx, cy, (short) region);
				out.append("cell ").append(cx).append(',').append(cy).append(" region ").append(region)
						.append(" model ").append(bc.model.length).append(" collision ").append(bc.collision.length)
						.append(" (painted ").append(before).append(", merged").append(merged).append(')')
						.append(" buildings ").append(here.size()).append(" door props ").append(doors.props.size())
						.append(note.isEmpty() ? "" : ": " + note.trim()).append('\n');
			}
		}
		matrix.write();
		// brush textures: straight from each donor area's world pack, as TerrainPrototype; building textures: the
		// painter's carry (it knows whether the donor keeps them in its world or prop pack)
		for (Map.Entry<Integer, Set<String>> e : brushNeeds.entrySet()) {
			AD src = new AD(Workspace.getWorkspaceFile(ArchiveType.AREA_DATA, e.getKey()), Workspace.session());
			staged.put(11, BchTexturePack.importTextures(staged.file(11), src.getFile(11), new ArrayList<>(e.getValue())));
		}
		for (Map.Entry<Integer, Set<String>> e : stampNeeds.entrySet()) {
			if (e.getKey() == area) {
				continue;
			}
			BchTexturePack.Carry carry = BchTexturePack.planCarry(Workspace.session(), e.getKey(), area,
					new ArrayList<>(e.getValue()), staged.file(11), staged.file(1), zone);
			if (carry.pack != null) {
				staged.put(carry.subfile, carry.pack);
			}
			out.append("carry from area ").append(e.getKey()).append(": ").append(carry.note.trim()).append('\n');
		}
		ctrmap.IslandArea.commit(staged);
		out.append(propNote.toString().trim().replace("\n", " | ")).append('\n');

		ZoneEntities ent = new ZoneEntities(zo.getFile(1));
		if (ent.npcs.isEmpty() || ent.npcs.get(0).uid != 0) {
			throw new IllegalStateException("zone " + zone + " has no NPC 0 (the ferry clerk)");
		}
		ZoneEntities.NPC npc = ent.npcs.get(0);
		npc.xTile = clerk[0];
		npc.yTile = clerk[1];
		npc.z3DCoordinate = (int) (rows.get(h + clerk[1]).charAt(clerk[0]) - '0') * (int) PaintedGeometry.STEP;
		npc.faceDirection = clerk[2];
		ent.npcs.clear();
		ent.npcs.add(npc);
		ent.furniture.clear();
		ent.triggers1.clear();
		ent.triggers2.clear();
		ent.warps.clear();
		for (Building b : buildings) {
			if (b.targetZone < 0) {
				continue;   // a building without a door warp
			}
			ZoneEntities.Warp wp = new ZoneEntities.Warp();
			wp.targetZone = b.targetZone;
			wp.targetWarpId = b.targetWarp;
			wp.faceDirection = 1;
			wp.transitionType = 3;
			wp.coordinateType = 0;
			wp.x = WorldGrid.tileCentre(b.doorX);
			wp.y = WorldGrid.tileCentre(b.doorY);
			wp.z = (rows.get(h + b.doorY).charAt(b.doorX) - '0') * (int) PaintedGeometry.STEP;
			wp.w = 1;
			wp.h = 1;
			ent.warps.add(wp);
			out.append("warp ").append(ent.warps.size() - 1).append(" door of ").append(b.name).append(" at tile ")
					.append(b.doorX).append(',').append(b.doorY).append(" z ").append(wp.z).append(" -> zone ")
					.append(b.targetZone).append(" warp ").append(b.targetWarp).append('\n');
		}
		out.append("clerk at tile ").append(npc.xTile).append(',').append(npc.yTile).append(" z ").append(npc.z3DCoordinate)
				.append(" face ").append(npc.faceDirection).append('\n');
		ent.modified = true;
		zo.storeFile(1, ent.assembleData());
		return out.toString().trim();
	}
}
