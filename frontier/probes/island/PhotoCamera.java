package faraway;

import ctrmap.Workspace;
import ctrmap.AreaForker;
import ctrmap.formats.cameradata.*;
import ctrmap.formats.containers.*;
import ctrmap.formats.zone.ZoneHeader;
import ctrmap.gamedef.ArchiveType;
import ctrmap.gamedef.GameType;
import java.io.File;

/** Disposable photo workspace ONLY. Never include its camera archive in production.
 * GAME WS [PITCH DISTANCE FOV]. With no camera arguments, inspect without writing.
 * Uses the editor's documented AD[3] format; does not alter models or movement.
 */
public final class PhotoCamera {
    public static void main(String[] a) throws Exception {
        if (a.length != 2 && a.length != 5)
            throw new IllegalArgumentException("GAME WS [PITCH DISTANCE FOV]");
        Session.open(new File(a[0]), new File(a[1]));
        ZO zo = new ZO(Workspace.getWorkspaceFile(ArchiveType.ZONE_DATA, 209), Workspace.session());
        ZoneHeader h = new ZoneHeader(zo.getFile(0), GameType.ORAS);
        AD ad = new AD(Workspace.getWorkspaceFile(ArchiveType.AREA_DATA, h.areadataID), Workspace.session());
        CameraDataFile table = new CameraDataFile(ad);
        System.out.println("PHOTO ONLY area=" + h.areadataID + " cameras=" + table.camData.size());
        for (CameraData c : table.camData) {
            CameraCoordinates v = c.coords1;
            System.out.println("bounds=" + c.boundX1 + "," + c.boundY1 + "," + c.boundX2 + "," + c.boundY2
                + " pitch=" + v.pitch + " yaw=" + v.yaw + " distance=" + v.distanceFromTarget + " fov=" + v.FOV);
        }
        if (a.length == 2) return;
        if (h.areadataID != 229 || AreaForker.areaSharers(209) != 0)
            throw new IllegalStateException("F11 private area 229 required");
        float pitch = Float.parseFloat(a[2]), distance = Float.parseFloat(a[3]), fov = Float.parseFloat(a[4]);
        if (!Float.isFinite(pitch) || !Float.isFinite(distance) || !Float.isFinite(fov)
            || pitch < -90 || pitch > -1 || distance <= 0 || fov <= 0 || fov >= 180)
            throw new IllegalArgumentException("Invalid photo camera");
        CameraData c = new CameraData();
        c.boundX1 = 0; c.boundY1 = 0; c.boundX2 = 159; c.boundY2 = 79;
        c.transitionPeriod = 0;
        for (CameraCoordinates v : new CameraCoordinates[]{c.coords1, c.coords2}) {
            v.pitch = pitch; v.distanceFromTarget = distance; v.FOV = fov;
        }
        table.camData.clear(); table.camData.add(c); table.write();
        System.out.println("PHOTO ONLY pitch=" + pitch + " distance=" + distance + " fov=" + fov);
        System.out.println("pack " + Workspace.packArchives((p,w)->{}));
    }
}
