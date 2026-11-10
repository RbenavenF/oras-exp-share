package faraway;

import ctrmap.MasterTable;
import ctrmap.Workspace;
import ctrmap.WorkspaceSession;
import ctrmap.formats.containers.ZO;
import ctrmap.formats.scripts.GFLPawnScript;
import ctrmap.formats.zone.Zone;
import ctrmap.formats.zone.ZoneEntities;
import ctrmap.gamedef.ArchiveType;
import ctrmap.gamedef.GameType;
import java.io.File;
import java.nio.file.Files;
import java.util.Properties;

/**
 * Builds the Faraway Island zones and the harbor changes into a staged copy of the game, through CTRMap-F5's
 * own operations (zone clone, map fork, area fork, NPC registry). Scripts come pre-assembled from
 * faraway/event.py; this program only places them.
 *
 * <p>Usage: Build game ws plan.properties. The plan names every number; nothing is chosen here.
 */
public final class Build {

	static final ctrmap.humaninterface.SaveHistory OPS = new ctrmap.humaninterface.SaveHistory(
			() -> java.util.Collections.<Object>emptyList());

	static Properties plan;
	static File scripts;

	public static void main(String[] a) throws Exception {
		Session.open(new File(a[0]), new File(a[1]));
		plan = new Properties();
		try (java.io.Reader r = Files.newBufferedReader(new File(a[2]).toPath())) {
			plan.load(r);
		}
		scripts = new File(plan.getProperty("scripts"));
		WorkspaceSession s = Workspace.session();
		for (String zone : plan.getProperty("clones").split(",")) {
			cloneZone(s, Integer.parseInt(zone.split(":")[1]), Integer.parseInt(zone.split(":")[0]));
		}
		for (String zone : plan.getProperty("zones").split(",")) {
			editZone(s, Integer.parseInt(zone));
		}
		System.out.println("pack " + Workspace.packArchives((p, what) -> { }));
	}

	static int num(String key) {
		String v = plan.getProperty(key);
		if (v == null) {
			throw new IllegalArgumentException("plan has no " + key);
		}
		return Integer.decode(v.trim());
	}

	/** Clone donor into slot with its own map and area, keeping the slot's text, script id and place name. */
	static void cloneZone(WorkspaceSession s, int slot, int donor) throws Exception {
		MasterTable before = MasterTable.read(s);
		byte[] row = before.row(slot);
		int text = u16(row, 0x06), script = u16(row, 0x18), place = u16(row, 0x1C);
		ZO old = zo(slot);
		byte[] oldEntities = old.getFile(1);
		ctrmap.WorkspaceOps.cloneWithOwnMap(s, donor, slot, OPS, () -> { });
		ctrmap.AreaForker.ForkResult area = ctrmap.AreaForker.forkIfShared(slot);
		System.out.println("zone " + slot + " cloned from " + donor + "; own map; area "
				+ (area == null ? "already private" : area.oldArea + " -> " + area.newArea));
		// Restore the slot's own identity: story text file, script id, place name. With keeptext.<slot> the
		// donor's story text stays (a clone that runs the donor's script needs the donor's messages).
		if (plan.getProperty("keeptext." + slot) != null) {
			text = u16(MasterTable.read(s).row(slot), 0x06);
		}
		if (plan.getProperty("text." + slot) != null) {
			text = num("text." + slot);
		}
		MasterTable table = MasterTable.read(s);
		byte[] r = table.row(slot);
		put16(r, 0x06, text);
		put16(r, 0x18, script);
		put16(r, 0x1C, (u16(r, 0x1C) & ~0x3FF) | (num("place." + slot) & 0x3FF));
		table.setRow(slot, r);
		table.write();
		ZO zo = zo(slot);
		byte[] h = zo.getFile(0);
		put16(h, 0x06, text);
		put16(h, 0x18, script);
		put16(h, 0x1C, (u16(h, 0x1C) & ~0x3FF) | (num("place." + slot) & 0x3FF));
		zo.storeFile(0, h);
		// Keep the placeholder's entity script (it does nothing); the donor's runs the donor's story setup.
		ZoneEntities placeholder = new ZoneEntities(oldEntities);
		ZoneEntities cloned = new ZoneEntities(zo.getFile(1));
		cloned.scripts = placeholder.scripts;
		cloned.modified = true;
		zo.storeFile(1, cloned.assembleData());
		System.out.println("zone " + slot + " keeps text " + text + ", script " + script + "; place " + num("place." + slot)
				+ " (was " + (place & 0x3FF) + ")");
	}

	static void editZone(WorkspaceSession s, int zoneIndex) throws Exception {
		String k = "zone." + zoneIndex + ".";
		Zone z = new Zone(zo(zoneIndex), GameType.ORAS);
		ZoneEntities e = z.entities;
		if (plan.getProperty(k + "clearNpcs") != null) {
			e.npcs.clear();
		}
		if (plan.getProperty(k + "clearTriggers") != null) {
			e.triggers1.clear();
			e.triggers2.clear();
		}
		for (int i = 0; plan.getProperty(k + "warp." + i) != null; i++) {
			String[] w = plan.getProperty(k + "warp." + i).split(",");
			ZoneEntities.Warp warp = e.warps.get(Integer.parseInt(w[0]));
			warp.targetZone = Integer.parseInt(w[1]);
			warp.targetWarpId = Integer.parseInt(w[2]);
		}
		for (int i = 0; plan.getProperty(k + "trigger." + i) != null; i++) {
			// script,work,value,x,y,w,h (tiles),height: fires while WorkGet(work) == value, like retail story triggers
			String[] t = plan.getProperty(k + "trigger." + i).split(",");
			ZoneEntities.Trigger trig = new ZoneEntities.Trigger();
			trig.script = Integer.parseInt(t[0].trim());
			trig.constant = Integer.parseInt(t[1].trim());
			trig.u2 = Integer.parseInt(t[2].trim());
			trig.x = Integer.parseInt(t[3].trim());
			trig.y = Integer.parseInt(t[4].trim());
			trig.w = Integer.parseInt(t[5].trim());
			trig.h = Integer.parseInt(t[6].trim());
			trig.u14 = Integer.parseInt(t[7].trim());   // height of the trigger plane (retail: the floor's)
			e.triggers1.add(trig);
		}
		ctrmap.formats.npcreg.NPCRegistry reg = new ctrmap.formats.npcreg.NPCRegistry(
				s.staged(ArchiveType.NPC_REGISTRIES, z.header.areadataID), s);
		boolean regChanged = false;
		for (int i = 0; plan.getProperty(k + "npc." + i) != null; i++) {
			// uid-free spec: model,moveModelsIndex,script,spawnFlag,x,y,z,face
			String[] n = plan.getProperty(k + "npc." + i).split(",");
			ZoneEntities.NPC npc = new ZoneEntities.NPC();
			npc.uid = e.npcs.size();
			npc.model = Integer.parseInt(n[0].trim());
			int moveModel = Integer.parseInt(n[1].trim());
			if (!reg.entries.containsKey(npc.model) && plan.getProperty("regnew." + npc.model) != null) {
				String fresh = plan.getProperty("regnew." + npc.model);
				if (fresh != null) {
					// A model new to the game: copy a retail entry (render, shadow, collision) and point it at the
					// appended MoveModels index. Format: templateArea,templateUid.
					String[] t = fresh.split(",");
					ctrmap.formats.npcreg.NPCRegistry tr = new ctrmap.formats.npcreg.NPCRegistry(
							s.staged(ArchiveType.NPC_REGISTRIES, Integer.parseInt(t[0].trim())), s);
					ctrmap.formats.npcreg.NPCRegistry.NPCRegistryEntry copy = copyEntry(tr.entries.get(Integer.parseInt(t[1].trim())));
					copy.model = moveModel;
					if (reg.register(copy, npc.model) != npc.model) {
						throw new IllegalStateException("uid " + npc.model + " is taken in area " + z.header.areadataID);
					}
					regChanged = true;
				}
			}
			if (!reg.entries.containsKey(npc.model)) {
				// The exact retail entry (collision size, render and shadow bits) from an area that has the model.
				int donorArea = num("regdonor." + npc.model);
				ctrmap.formats.npcreg.NPCRegistry donor = new ctrmap.formats.npcreg.NPCRegistry(
						s.staged(ArchiveType.NPC_REGISTRIES, donorArea), s);
				ctrmap.formats.npcreg.NPCRegistry.NPCRegistryEntry source = donor.entries.get(npc.model);
				if (source == null || source.model != moveModel) {
					throw new IllegalStateException("area " + donorArea + " has no entry " + npc.model + " for model " + moveModel);
				}
				ctrmap.formats.npcreg.NPCRegistry.NPCRegistryEntry copy = copyEntry(source);
				int uid = reg.register(copy, npc.model);
				if (uid != npc.model) {
					throw new IllegalStateException("registry gave uid " + uid + " for model " + npc.model);
				}
				regChanged = true;
			}
			npc.script = Integer.parseInt(n[2].trim());
			npc.spawnFlag = Integer.parseInt(n[3].trim());
			npc.xTile = Integer.parseInt(n[4].trim());
			npc.yTile = Integer.parseInt(n[5].trim());
			npc.z3DCoordinate = Float.parseFloat(n[6].trim());
			npc.faceDirection = Integer.parseInt(n[7].trim());
			npc.multiZoneLinkOriginZone = -1;
			npc.multiZoneLinkTargetZone = -1;
			npc.multiZoneLinkHostZone = -1;
			e.npcs.add(npc);
		}
		e.modified = true;
		File zs = new File(scripts, "zone" + zoneIndex + ".bin");
		if (zs.isFile()) {
			z.s = new GFLPawnScript(Files.readAllBytes(zs.toPath()));
		}
		File es = new File(scripts, "zone" + zoneIndex + ".ent.bin");
		if (es.isFile()) {
			e.scripts = new GFLPawnScript(Files.readAllBytes(es.toPath()));
		}
		z.store();
		if (regChanged) {
			reg.store();
		}
		if (plan.getProperty(k + "loadBudget") != null) {
			String budget = ctrmap.tests.FrontierPlaza.loadBudget(zoneIndex);
			System.out.println("zone " + zoneIndex + " " + budget);
			if (Long.parseLong(budget.split(" ")[2]) > num(k + "loadBudget")) {
				throw new IllegalStateException("zone " + zoneIndex + " exceeds load budget");
			}
		}
		System.out.println("zone " + zoneIndex + ": " + e.npcs.size() + " NPCs, " + e.warps.size() + " warps, "
				+ e.triggers1.size() + " triggers; scripts " + zs.isFile() + "/" + es.isFile() + "; registry "
				+ (regChanged ? "extended" : "as is") + " (area " + z.header.areadataID + ")");
	}

	static ctrmap.formats.npcreg.NPCRegistry.NPCRegistryEntry copyEntry(ctrmap.formats.npcreg.NPCRegistry.NPCRegistryEntry t) {
		ctrmap.formats.npcreg.NPCRegistry.NPCRegistryEntry e = new ctrmap.formats.npcreg.NPCRegistry.NPCRegistryEntry();
		for (java.lang.reflect.Field f : e.getClass().getFields()) {
			try {
				f.set(e, f.get(t));
			} catch (IllegalAccessException ex) {
				throw new IllegalStateException(ex);
			}
		}
		return e;
	}

	static ZO zo(int zone) {
		return new ZO(Workspace.getWorkspaceFile(ArchiveType.ZONE_DATA, zone), Workspace.session());
	}

	static int u16(byte[] b, int o) {
		return (b[o] & 0xFF) | (b[o + 1] & 0xFF) << 8;
	}

	static void put16(byte[] b, int o, int v) {
		b[o] = (byte) v;
		b[o + 1] = (byte) (v >> 8);
	}
}
