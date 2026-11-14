package faraway;

import ctrmap.*;
import ctrmap.formats.containers.*;
import ctrmap.formats.mapmatrix.MapMatrix;
import ctrmap.formats.zone.ZoneHeader;
import ctrmap.gamedef.*;
import java.io.File;

/** Read-only census of GR[4]'s row/column against each matrix's populated cells. */
public final class GRCoordinates {
    public static void main(String[] args) throws Exception {
        if (args.length != 2) throw new IllegalArgumentException("GAME WS");
        Session.open(new File(args[0]), new File(args[1]));
        for (int zone : new int[]{16,18,61,210,211,212,209}) {
            ZoneHeader header = new ZoneHeader(new ZO(Workspace.getWorkspaceFile(
                ArchiveType.ZONE_DATA, zone), Workspace.session()).getFile(0), GameType.ORAS);
            MapMatrix matrix = new MapMatrix(new MM(Workspace.getWorkspaceFile(
                ArchiveType.MAP_MATRIX, header.mapmatrixID), Workspace.session()), Workspace.session());
            int count = 0, matches = 0;
            for (int y=0; y<matrix.height; y++) for (int x=0; x<matrix.width; x++) {
                int region = matrix.ids.get(x,y);
                if (region < 0) continue;
                byte[] data = new GR(Workspace.getWorkspaceFile(ArchiveType.FIELD_DATA,
                    region), Workspace.session()).getFile(4);
                if (data.length < 2) throw new IllegalStateException("Missing GR[4]: " + region);
                count++;
                int row = data[0]&255, column = data[1]&255;
                if (row == y && column == x) matches++;
                else System.out.println("MISMATCH zone="+zone+" region="+region+
                    " expected="+y+","+x+" got="+row+","+column);
            }
            System.out.println("zone="+zone+" matrix="+header.mapmatrixID+
                " size="+matrix.width+"x"+matrix.height+" GR[4] coordinates match="+matches+"/"+count);
        }
    }
}
