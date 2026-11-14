package faraway;

import ctrmap.*;
import ctrmap.formats.containers.*;
import ctrmap.formats.h3d.*;
import ctrmap.formats.mapmatrix.MapMatrix;
import ctrmap.formats.tilemap.*;
import ctrmap.formats.zone.*;
import ctrmap.gamedef.ArchiveType;
import java.io.File;
import java.nio.file.*;
import java.util.*;

/** F11 laboratory only: rebuild zone 209's private matrix as eight terrain cells, one area. */
public final class TerrainPrototype {
    static TilePalette brush(char c) {
        switch(c) {
            case '~': case 'w': return TilePalette.WATER;
            case ',': case 'T': case 'p': return TilePalette.GRASS;
            case 's': return TilePalette.SAND;
            case '=': return TilePalette.STAIRS_Z;
            case '#': case 'o': case 'f': case 'x': case 'B': return TilePalette.ROCK;
            default: return TilePalette.PATH;
        }
    }
    public static void main(String[] a) throws Exception {
        Session.open(new File(a[0]), new File(a[1]));
        List<String> data=Files.readAllLines(Paths.get(a[2]));
        if(data.size()!=160) throw new IllegalArgumentException("80 class rows + 80 height rows required");
        int zone=209, area=AreaForker.currentArea(zone);
        if(AreaForker.areaSharers(zone)>0) throw new IllegalStateException("Private area required");
        ZO zo=new ZO(Workspace.getWorkspaceFile(ArchiveType.ZONE_DATA,zone),Workspace.session());
        ZoneHeader hdr=new ZoneHeader(zo.getFile(0),ctrmap.gamedef.GameType.ORAS);
        MM mm=new MM(Workspace.getWorkspaceFile(ArchiveType.MAP_MATRIX,hdr.mapmatrixID),Workspace.session());
        MapMatrix matrix=new MapMatrix(mm,4,2,0);
        matrix.cambounds.get(0).east=160*18;
        matrix.cambounds.get(0).south=80*18;
        int first=GeometryForker.nextFreeRegion(Workspace.session(),Workspace.getArchive(ArchiveType.FIELD_DATA));
        GR nativeRegion=BuildingCatalog.pristineRegion(Workspace.session(),489);
        byte[] donor=nativeRegion.getFile(1);
        System.out.println("Retail GR slots="+nativeRegion.len+" (preserving auxiliary subfiles)");
        Map<Integer,Set<String>> needs=new LinkedHashMap<>();
        AD ad=new AD(Workspace.getWorkspaceFile(ArchiveType.AREA_DATA,area),Workspace.session());
        for(int cy=0;cy<2;cy++) for(int cx=0;cx<4;cx++) {
            TilePalette[][] grid=new TilePalette[40][40]; int[][] height=new int[40][40],ramp=new int[40][40];
            for(int y=0;y<40;y++) for(int x=0;x<40;x++) {
                int gx=cx*40+x,gy=cy*40+y;
                grid[y][x]=brush(data.get(gy).charAt(gx));
                height[y][x]=data.get(80+gy).charAt(gx)-'0'; ramp[y][x]=PaintedGeometry.NO_RAMP;
            }
            byte[] template=MapPainter.importBrushMaterials(donor,grid,null,needs);
            RegionFactory.BlankContent bc=PaintedRegionBuilder.build(Workspace.session(),template,grid,height,ramp,TerrainLighting.daytime(),false);
            // Keep the generated stair slope, but use ordinary walking in this
            // terrain-only lab: 0x6c blocked this prototype's reception step.
            for(int y=0;y<40;y++) for(int x=0;x<40;x++)
                if(grid[y][x]==TilePalette.STAIRS_Z) bc.tilemap[4+(y*40+x)*4+3]=0;
            int region=first+cy*4+cx;
            File out=new File(Workspace.getExtractionDirectory(ArchiveType.FIELD_DATA),String.valueOf(region));
            // ORAS carries a seventh KAGE subfile: retain the retail container shape,
            // including auxiliary fields, instead of synthesizing a six-slot XY GR.
            Files.copy(nativeRegion.getOriginFile().toPath(),out.toPath(),StandardCopyOption.REPLACE_EXISTING);
            GR gr=new GR(out,Workspace.session());
            gr.storeFile(0,bc.tilemap);gr.storeFile(1,bc.model);gr.storeFile(2,bc.collision);gr.storeFile(3,bc.props);
            Workspace.session().registerPendingCompression(ArchiveType.FIELD_DATA,region,true);
            matrix.ids.set(cx,cy,(short)region);
            System.out.println("CELL " + cx+","+cy+" region="+region+" model="+bc.model.length+" collision="+bc.collision.length);
        }
        matrix.write();
        byte[] world=ad.getFile(11);
        for(Map.Entry<Integer,Set<String>> e:needs.entrySet()) {
            AD src=new AD(Workspace.getWorkspaceFile(ArchiveType.AREA_DATA,e.getKey()),Workspace.session());
            world=BchTexturePack.importTextures(world,src.getFile(11),new ArrayList<>(e.getValue()));
        }
        ad.storeFile(11,world);
        ZoneEntities ent=new ZoneEntities(zo.getFile(1));
        ent.npcs.clear();ent.warps.clear();ent.furniture.clear();ent.triggers1.clear();ent.triggers2.clear();
        zo.storeFile(1,ent.assembleData());
        System.out.println("pack " + Workspace.packArchives((p,what)->{}));
        System.out.println("outside the world pack: " + ctrmap.tests.FrontierPlaza.worldTexturesOutsideWorldPack(zone));
        System.out.println(ctrmap.tests.FrontierPlaza.loadBudget(zone));
    }
}
