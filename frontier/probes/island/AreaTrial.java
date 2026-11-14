package faraway;

import ctrmap.*;
import ctrmap.formats.containers.*;
import ctrmap.formats.h3d.*;
import ctrmap.formats.gfcollision.GfColl;
import ctrmap.formats.mapmatrix.MapMatrix;
import ctrmap.formats.zone.ZoneHeader;
import ctrmap.gamedef.ArchiveType;
import java.io.File;
import java.util.*;

/** Isolated F11 diagnosis. Only use on the disposable game/ws made by build.py. */
public final class AreaTrial {
    public static void main(String[] a) throws Exception {
        if (a.length != 3 || !Arrays.asList("world", "props", "lod", "compact", "names", "animations", "flatcollision", "retailmodels", "camera", "coordinates").contains(a[2]))
            throw new IllegalArgumentException("GAME WS world|props|lod|compact|names|animations|flatcollision|retailmodels|camera|coordinates; trials are cumulative");
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
        } else if (a[2].equals("coordinates")) {
            // Retail 489..492: GR[4] begins {row,column,0,0}, then float 18.
            // Diagnose whether cloning {0,0} into every cell breaks reloading.
            for(int y=0;y<matrix.height;y++) for(int x=0;x<matrix.width;x++) {
                int region=matrix.ids.get(x,y);
                GR gr=new GR(Workspace.getWorkspaceFile(ArchiveType.FIELD_DATA,region),Workspace.session());
                byte[] extended=gr.getFile(4).clone();
                if(extended.length<8) throw new IllegalStateException("extended GR header missing");
                extended[0]=(byte)y;extended[1]=(byte)x;
                gr.storeFile(4,extended);
                Workspace.session().registerPendingCompression(ArchiveType.FIELD_DATA,region,true);
                System.out.println("GR coordinates "+region+" row="+y+" column="+x);
            }
        } else if (a[2].equals("camera")) {
            AD empty=new AD(Workspace.getWorkspaceFile(ArchiveType.AREA_DATA,0),Workspace.session());
            ad.storeFile(3,empty.getFile(3));
            System.out.println("Camera table from area 0: " + empty.getFile(3).length);
        } else if (a[2].equals("retailmodels")) {
            Set<String> needed=new TreeSet<>();
            for(int y=0;y<matrix.height;y++) for(int x=0;x<matrix.width;x++) {
                int region=matrix.ids.get(x,y);
                GR donor=BuildingCatalog.pristineRegion(Workspace.session(),489+y*2+x%2);
                BchMapModel model=new BchMapModel(donor.getFile(1));
                for(int mesh=0;mesh<model.meshes.size();mesh++)
                    needed.addAll(model.getMaterialTextureNames(model.getMeshMaterialIndex(mesh)));
                GR gr=new GR(Workspace.getWorkspaceFile(ArchiveType.FIELD_DATA,region),Workspace.session());
                gr.storeFile(1,donor.getFile(1));
                Workspace.session().registerPendingCompression(ArchiveType.FIELD_DATA,region,true);
            }
            AD nativeArea=new AD(Workspace.getWorkspaceFile(ArchiveType.AREA_DATA,101),Workspace.session());
            byte[] world=nativeArea.getFile(11);
            Set<String> present=new TreeSet<>();
            for(BchTexturePack.Texture t:BchTexturePack.parse(world)) present.add(t.name);
            List<String> found=new ArrayList<>();
            for(BchTexturePack.Texture t:BchTexturePack.parse(nativeArea.getFile(1)))
                if(needed.contains(t.name) && !present.contains(t.name)) found.add(t.name);
            world=BchTexturePack.importTextures(world,nativeArea.getFile(1),found);
            ad.storeFile(11,world);
            System.out.println("Diagnostic retail harbor models on the 4x2 matrix");
        } else if (a[2].equals("flatcollision")) {
            // Diagnostic only: visible terrain and movement tuples stay intact;
            // collision becomes a flat platform at the reload fixture's height.
            byte[] flat = GfColl.build(Arrays.asList(
                new float[]{-360,36,-360,-360,36,360,360,36,-360},
                new float[]{360,36,-360,-360,36,360,360,36,360}), null);
            for (int y=0;y<matrix.height;y++) for(int x=0;x<matrix.width;x++) {
                int region=matrix.ids.get(x,y);
                GR gr=new GR(Workspace.getWorkspaceFile(ArchiveType.FIELD_DATA,region),Workspace.session());
                gr.storeFile(2,flat);
                Workspace.session().registerPendingCompression(ArchiveType.FIELD_DATA,region,true);
            }
            System.out.println("Diagnostic flat collision " + flat.length);
        } else if (a[2].equals("animations")) {
            // No building props in this prototype: omit their inherited material animations.
            // Area 0 supplies a retail, valid empty animation BCH rather than a zero blob.
            AD empty = new AD(Workspace.getWorkspaceFile(ArchiveType.AREA_DATA, 0), Workspace.session());
            ad.storeFile(2, empty.getFile(2));
            System.out.println("Animation BCH " + empty.getFile(2).length + " bytes from area 0");
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
