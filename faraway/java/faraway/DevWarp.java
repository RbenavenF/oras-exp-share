package faraway;

import ctrmap.Workspace;
import ctrmap.formats.containers.ZO;
import ctrmap.formats.zone.Zone;
import ctrmap.formats.zone.ZoneEntities;
import ctrmap.gamedef.ArchiveType;
import ctrmap.gamedef.GameType;
import java.io.File;

/**
 * DEVELOPMENT ONLY: adds a large warp rectangle to a zone so that the next step sends the player to another
 * zone's warp. Used to look at candidate maps in the emulator; never part of the delivered package.
 *
 * <p>Usage: DevWarp game ws sourceZone tileX tileY width height targetZone targetWarp
 */
public final class DevWarp {

	public static void main(String[] a) throws Exception {
		Session.open(new File(a[0]), new File(a[1]));
		int source = Integer.parseInt(a[2]);
		Zone z = new Zone(new ZO(Workspace.getWorkspaceFile(ArchiveType.ZONE_DATA, source), Workspace.session()), GameType.ORAS);
		ZoneEntities.Warp w = new ZoneEntities.Warp();
		w.x = Integer.parseInt(a[3]) * 18 + 9;
		w.y = Integer.parseInt(a[4]) * 18 + 9;
		w.w = Integer.parseInt(a[5]);
		w.h = Integer.parseInt(a[6]);
		w.targetZone = Integer.parseInt(a[7]);
		w.targetWarpId = Integer.parseInt(a[8]);
		w.z = a.length > 9 ? Integer.parseInt(a[9]) : 0;
		w.directionality = 0;
		w.faceDirection = a.length > 10 ? Integer.parseInt(a[10]) : 1;
		w.transitionType = 3;
		z.entities.warps.add(w);
		z.entities.modified = true;
		System.out.println("stored " + z.store());
		System.out.println("pack " + Workspace.packArchives((p, what) -> { }));
	}
}
