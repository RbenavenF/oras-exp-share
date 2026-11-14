package faraway;

import ctrmap.*;
import ctrmap.formats.containers.*;
import ctrmap.formats.h3d.*;
import ctrmap.formats.mapmatrix.MapMatrix;
import ctrmap.formats.zone.ZoneHeader;
import ctrmap.gamedef.ArchiveType;
import java.io.File;
import java.util.*;

/** Isolated F11 diagnosis. Only use on the disposable game/ws made by build.py. */
public final class AreaTrial {
    public static void main(String[] a) throws Exception {
        if (a.length != 3 || !Arrays.asList("world", "props", "lod", "compact", "names").contains(a[2]))
            throw new IllegalArgumentException("GAME WS world|props|lod|compact|names; trials are cumulative");
        Session.open(new File(a[0]), new File(a[1]));
        ZO zo = new ZO(Workspace.getWorkspaceFile(ArchiveType.ZONE_DATA, 209), Workspace.session());
        ZoneHeader hdr = new ZoneHeader(zo.getFile(0), ctrmap.gamedef.GameType.ORAS);
        if (AreaForker.areaSharers(209) != 0) throw new IllegalStateException("private area required");
        MapMatrix matrix = new MapMatrix(new MM(Workspace.getWorkspaceFile(ArchiveType.MAP_MATRIX,
            hdr.mapmatrixID), Workspace.session()), Workspace.session());
        if (matrix.width != 4 || matrix.height != 2) throw new IllegalStateException("F11 4x2 required");
        AD ad = new AD(Workspace.getWorkspaceFile(ArchiveType.AREA_DATA, hdr.areadataID), Workspace.session());
        if (a[2].equals("world")) {
            Set<String> needed = new TreeSet<>();
            for (int y=0; y<matrix.height; y++) for (int x=0; x<matrix.width; x++) {
                GR gr = new GR(Workspace.getWorkspaceFile(ArchiveType.FIELD_DATA, matrix.ids.get(x,y)), Workspace.session());
                BchMapModel model = new BchMapModel(gr.getFile(1));
                for (int mesh=0; mesh<model.meshes.size(); mesh++)
                    needed.addAll(model.getMaterialTextureNames(model.getMeshMaterialIndex(mesh)));
            }
            List<BchTexturePack.Texture> keep = new ArrayList<>();
            for (BchTexturePack.Texture t : BchTexturePack.parse(ad.getFile(11))) {
                System.out.println((needed.contains(t.name) ? "KEEP " : "DROP ") + t.name + " " + t.data.length);
                if (needed.contains(t.name)) keep.add(t);
            }
            ad.storeFile(11, BchTexturePack.emit(keep));
        } else if (a[2].equals("props")) {
            // No props exist in this prototype. Keep a valid one-texture BCH sentinel.
            for (int y=0; y<matrix.height; y++) for (int x=0; x<matrix.width; x++) {
                GR gr = new GR(Workspace.getWorkspaceFile(ArchiveType.FIELD_DATA, matrix.ids.get(x,y)), Workspace.session());
                if (ctrmap.util.LittleEndian.i32(gr.getFile(3),0) != 0)
                    throw new IllegalStateException("props must be absent");
            }
            ad.storeFile(0, new byte[4]);
            List<BchTexturePack.Texture> textures = BchTexturePack.parse(ad.getFile(1));
            textures.sort((x,y) -> Integer.compare(x.data.length,y.data.length));
            ad.storeFile(1, BchTexturePack.emit(Collections.singletonList(textures.get(0))));
            System.out.println("Prop sentinel " + textures.get(0).name + " " + textures.get(0).data.length);
        } else if (a[2].equals("names")) {
            for (int y=0; y<matrix.height; y++) for (int x=0; x<matrix.width; x++) {
                int region=matrix.ids.get(x,y);
                GR gr=new GR(Workspace.getWorkspaceFile(ArchiveType.FIELD_DATA,region),Workspace.session());
                BchMapModel model=new BchMapModel(gr.getFile(1));
                String old=model.getModelName(), name=String.format(java.util.Locale.ROOT,"battle03_%02d_%02d",x,y);
                if (!old.matches("battle03_[0-9]{2}_[0-9]{2}") || old.length()!=name.length())
                    throw new IllegalStateException("unexpected model name "+old);
                byte[] bytes=model.raw.clone(), from=old.getBytes("US-ASCII"), to=name.getBytes("US-ASCII");
                int changed=0;
                for (int p=model.stringsAddr; p+from.length<=model.stringsAddr+model.stringsLen; p++) {
                    boolean match=true;
                    for(int k=0;k<from.length;k++)if(bytes[p+k]!=from[k])match=false;
                    if(match){System.arraycopy(to,0,bytes,p,to.length);changed++;p+=from.length-1;}
                }
                BchMapModel check=new BchMapModel(bytes);
                if(changed==0 || !check.getModelName().equals(name) || !check.validate().isEmpty())
                    throw new IllegalStateException("model rename failed");
                System.out.println("NAME "+region+" "+old+" -> "+name+" strings="+changed);
                gr.storeFile(1,bytes);
                Workspace.session().registerPendingCompression(ArchiveType.FIELD_DATA,region,true);
            }
        } else if (a[2].equals("compact")) {
            for (int y=0; y<matrix.height; y++) for (int x=0; x<matrix.width; x++) {
                int region=matrix.ids.get(x,y);
                GR gr=new GR(Workspace.getWorkspaceFile(ArchiveType.FIELD_DATA,region),Workspace.session());
                gr.storeFile(1, CompactFloors.compact(gr.getFile(1)));
                Workspace.session().registerPendingCompression(ArchiveType.FIELD_DATA,region,true);
            }
        } else {
            matrix.hasLOD=1;
            for (int y=0; y<matrix.height*4; y++) for (int x=0; x<matrix.width*4; x++)
                matrix.zones.set(x,y,(short)209);
            matrix.write();
        }
        System.out.println("pack " + Workspace.packArchives((p,w)->{}));
        System.out.println("outside world pack " + ctrmap.tests.FrontierPlaza.worldTexturesOutsideWorldPack(209));
        System.out.println(ctrmap.tests.FrontierPlaza.loadBudget(209));
    }
}
