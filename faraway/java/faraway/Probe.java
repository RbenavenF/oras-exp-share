package faraway;

import ctrmap.Workspace;
import ctrmap.WorkspaceSession;
import ctrmap.ZoneTables;
import ctrmap.formats.containers.ContainerBytes;
import ctrmap.formats.text.LocationNames;
import ctrmap.formats.zone.ZoneEntities;
import ctrmap.formats.zone.ZoneHeader;
import ctrmap.gamedef.ArchiveType;
import java.io.File;

/** Read-only survey of the staged game: zones, names, entity counts and repurpose candidates. */
public final class Probe {

	public static void main(String[] args) throws Exception {
		Session.open(new File(args[0]), new File(args[1]));
		WorkspaceSession s = Workspace.session();
		String mode = args.length > 2 ? args[2] : "zones";
		if (mode.equals("zones")) {
			int zones = ZoneTables.zoneCount(s.getArchive(ArchiveType.ZONE_DATA));
			System.out.println("zones " + zones);
			for (int z = 0; z < zones; z++) {
				byte[] zo = ZoneTables.zoneNow(s, z);
				byte[] hdr = ContainerBytes.subfile(zo, 0);
				ZoneHeader h = new ZoneHeader(hdr, ctrmap.gamedef.GameType.ORAS);
				ZoneEntities e = new ZoneEntities(ContainerBytes.subfile(zo, 1));
				System.out.printf("%d\t%s\tparent=%d\tarea=%d\tmatrix=%d\ttext=%d\tscript=%d\tnpc=%d\twarp=%d\ttrig=%d/%d\tprops=%d%n",
						z, LocationNames.getLocName(s, h.parentMap), h.parentMap, h.areadataID, h.mapmatrixID, h.textID,
						h.script, e.npcs.size(), e.warps.size(), e.triggers1.size(), e.triggers2.size(), e.furniture.size());
			}
		} else if (mode.equals("repurpose")) {
			System.out.println(ctrmap.ZoneRepurposeScanner.report(ctrmap.ZoneRepurposeScanner.scanZones(s)));
		} else if (mode.equals("disasm")) {
			for (int i = 3; i < args.length; i++) {
				int z = Integer.parseInt(args[i]);
				byte[] zo = ZoneTables.zoneNow(s, z);
				ctrmap.formats.scripts.GFLPawnScript scr = new ctrmap.formats.scripts.GFLPawnScript(ContainerBytes.subfile(zo, 2));
				System.out.println("// zone " + z);
				System.out.println(ctrmap.humaninterface.ScriptEditor.getDisassemblyTextForArea(scr));
			}
		} else if (mode.equals("entities")) {
			for (int i = 3; i < args.length; i++) {
				int z = Integer.parseInt(args[i]);
				ZoneEntities e = new ZoneEntities(ContainerBytes.subfile(ZoneTables.zoneNow(s, z), 1));
				System.out.println("// zone " + z);
				for (int k = 0; k < e.npcs.size(); k++) {
					ZoneEntities.NPC n = e.npcs.get(k);
					System.out.printf("npc %d uid=%d model=%d script=%d spawnFlag=%d move=%d/%d face=%d sight=%d at=(%d,%d) z=%.1f%n",
							k, n.uid, n.model, n.script, n.spawnFlag, n.movePerm1, n.movePerm2, n.faceDirection, n.sightRange, n.xTile, n.yTile, n.z3DCoordinate);
				}
				for (int k = 0; k < e.furniture.size(); k++) {
					ZoneEntities.Prop f = e.furniture.get(k);
					System.out.printf("prop %d script=%d%n", k, f.script);
				}
				for (int k = 0; k < e.warps.size(); k++) {
					ZoneEntities.Warp w = e.warps.get(k);
					System.out.printf("warp %d -> zone %d warp %d dir=%d face=%d trans=%d coord=%d at=(%d,%d,%d) size=%dx%d%n",
							k, w.targetZone, w.targetWarpId, w.directionality, w.faceDirection, w.transitionType, w.coordinateType, w.x, w.y, w.z, w.w, w.h);
				}
				for (ZoneEntities.Trigger t : e.triggers1) {
					System.out.printf("trigger1 script=%d const=%d u2=%d u6=%d u8=%d at=(%d,%d) size=%dx%d%n", t.script, t.constant, t.u2, t.u6, t.u8, t.x, t.y, t.w, t.h);
				}
				for (ZoneEntities.Trigger t : e.triggers2) {
					System.out.printf("trigger2 script=%d const=%d u2=%d u6=%d u8=%d at=(%d,%d) size=%dx%d%n", t.script, t.constant, t.u2, t.u6, t.u8, t.x, t.y, t.w, t.h);
				}
			}
		} else if (mode.equals("shared")) {
			ctrmap.formats.garc.GARC g = s.getArchive(ArchiveType.SHARED_SCRIPTS);
			File dir = new File(args[3]);
			dir.mkdirs();
			for (int i = 0; i < g.length; i++) {
				try {
					ctrmap.formats.scripts.GFLPawnScript scr = new ctrmap.formats.scripts.GFLPawnScript(g.getDecompressedEntry(i));
					java.nio.file.Files.write(new File(dir, "shared" + i + ".asm").toPath(),
							ctrmap.humaninterface.ScriptEditor.getDisassemblyTextForArea(scr).getBytes("UTF-8"));
				} catch (Exception ex) {
					System.out.println("shared " + i + ": " + ex);
				}
			}
		} else if (mode.equals("alldisasm")) {
			File dir = new File(args[3]);
			dir.mkdirs();
			int zones = ZoneTables.zoneCount(s.getArchive(ArchiveType.ZONE_DATA));
			for (int z = 0; z < zones; z++) {
				try {
					ctrmap.formats.scripts.GFLPawnScript scr = new ctrmap.formats.scripts.GFLPawnScript(ContainerBytes.subfile(ZoneTables.zoneNow(s, z), 2));
					java.nio.file.Files.write(new File(dir, "zone" + z + ".asm").toPath(),
							ctrmap.humaninterface.ScriptEditor.getDisassemblyTextForArea(scr).getBytes("UTF-8"));
					ZoneEntities e = new ZoneEntities(ContainerBytes.subfile(ZoneTables.zoneNow(s, z), 1));
					java.nio.file.Files.write(new File(dir, "zone" + z + ".ent.asm").toPath(),
							ctrmap.humaninterface.ScriptEditor.getDisassemblyTextForArea(e.scripts).getBytes("UTF-8"));
				} catch (Exception ex) {
					System.out.println("zone " + z + ": " + ex);
				}
			}
		} else if (mode.equals("models")) {
			int n = ctrmap.formats.npcreg.MoveModelPool.size(s);
			for (int i = 0; i < n; i++) {
				System.out.println(i + "\t" + ctrmap.formats.npcreg.MoveModelPool.name(s, i));
			}
		} else if (mode.equals("registry")) {
			for (int i = 3; i < args.length; i++) {
				int area = Integer.parseInt(args[i]);
				ctrmap.formats.npcreg.NPCRegistry r = new ctrmap.formats.npcreg.NPCRegistry(s.staged(ArchiveType.NPC_REGISTRIES, area), s);
				System.out.println("// area " + area);
				for (ctrmap.formats.npcreg.NPCRegistry.NPCRegistryEntry e : r.inFileOrder()) {
					System.out.println("uid " + e.uid + " model " + e.model + " " + ctrmap.formats.npcreg.MoveModelPool.name(s, e.model));
				}
			}
		} else if (mode.equals("floor")) {
			// Top-down floor map: one character per tile; '#' where the collision has no floor.
			int z = Integer.parseInt(args[3]);
			ZoneHeader h = new ZoneHeader(ContainerBytes.subfile(ZoneTables.zoneNow(s, z), 0), ctrmap.gamedef.GameType.ORAS);
			byte[] mm = java.nio.file.Files.readAllBytes(s.staged(ArchiveType.MAP_MATRIX, h.mapmatrixID).toPath());
			ctrmap.formats.mapmatrix.MapMatrix.Grid g = ctrmap.formats.mapmatrix.MapMatrix.Grid.of(mm);
			System.out.println("// zone " + z + " matrix " + h.mapmatrixID + " " + g.width + "x" + g.height);
			int x0 = args.length > 4 ? Integer.parseInt(args[4]) : 0, x1 = args.length > 5 ? Integer.parseInt(args[5]) : g.width * 40;
			int y0 = args.length > 6 ? Integer.parseInt(args[6]) : 0, y1 = args.length > 7 ? Integer.parseInt(args[7]) : g.height * 40;
			float[][][] cells = new float[g.cells()][][];
			for (int k = 0; k < g.cells(); k++) {
				if (g.id(k) != 0xFFFF) {
					byte[] fd = java.nio.file.Files.readAllBytes(s.staged(ArchiveType.FIELD_DATA, g.id(k)).toPath());
					cells[k] = ctrmap.formats.tilemap.PaintedHeights.sampleBaseY(ContainerBytes.subfile(fd, 2));
				}
			}
			ZoneEntities e = new ZoneEntities(ContainerBytes.subfile(ZoneTables.zoneNow(s, z), 1));
			StringBuilder header = new StringBuilder("     ");
			for (int x = x0; x < x1; x++) header.append(x % 10);
			System.out.println(header);
			for (int y = y0; y < y1; y++) {
				StringBuilder row = new StringBuilder(String.format("%4d ", y));
				for (int x = x0; x < x1; x++) {
					int k = (y / 40) * g.width + x / 40;
					char c = '#';
					if (cells[k] != null && !Float.isNaN(cells[k][y % 40][x % 40])) {
						int v = Math.round(cells[k][y % 40][x % 40]);
						c = (char) ('a' + Math.floorMod(v / 18, 26));
					}
					for (ZoneEntities.NPC n : e.npcs) if (n.xTile == x && n.yTile == y) c = (char) ('0' + n.uid % 10);
					for (ZoneEntities.Warp w : e.warps) if (x >= w.x / 18 && x < w.x / 18 + w.w && y >= w.y / 18 && y < w.y / 18 + w.h) c = 'W';
					row.append(c);
				}
				System.out.println(row);
			}
		} else if (mode.equals("tuples")) {
			// Tilemap tuples (4 bytes per tile) over a rectangle of tiles: tuples ZONE X0 X1 Y0 Y1
			int z = Integer.parseInt(args[3]);
			ZoneHeader h = new ZoneHeader(ContainerBytes.subfile(ZoneTables.zoneNow(s, z), 0), ctrmap.gamedef.GameType.ORAS);
			byte[] mm = java.nio.file.Files.readAllBytes(s.staged(ArchiveType.MAP_MATRIX, h.mapmatrixID).toPath());
			ctrmap.formats.mapmatrix.MapMatrix.Grid g = ctrmap.formats.mapmatrix.MapMatrix.Grid.of(mm);
			int x0 = Integer.parseInt(args[4]), x1 = Integer.parseInt(args[5]), y0 = Integer.parseInt(args[6]), y1 = Integer.parseInt(args[7]);
			for (int y = y0; y <= y1; y++) {
				StringBuilder row = new StringBuilder(String.format("%4d ", y));
				for (int x = x0; x <= x1; x++) {
					int k = (y / 40) * g.width + x / 40;
					byte[] fd = java.nio.file.Files.readAllBytes(s.staged(ArchiveType.FIELD_DATA, g.id(k)).toPath());
					byte[] tm = ContainerBytes.subfile(fd, 0);
					int off = 4 + ((y % 40) * 40 + x % 40) * 4;
					row.append(String.format("%02x%02x%02x%02x ", tm[off], tm[off + 1], tm[off + 2], tm[off + 3]));
				}
				System.out.println(row);
			}
		} else if (mode.equals("repurpose")) {
			System.out.println(ctrmap.ZoneRepurposeScanner.report(ctrmap.ZoneRepurposeScanner.scanZones(s)));
		}
	}
}
