package faraway;

import ctrmap.Workspace;
import ctrmap.formats.containers.*;
import ctrmap.formats.mapmatrix.MapMatrix;
import ctrmap.formats.zone.ZoneHeader;
import ctrmap.gamedef.ArchiveType;
import ctrmap.tests.FrontierIsland;
import ctrmap.tests.FrontierPlaza;
import ctrmap.tests.IslandLandscape;
import java.io.File;
import java.nio.file.Files;
import java.util.*;

/** Runs a trial against a COPY of the built production island, with movement snapshotted. */
public final class LandscapeTrial {
    public static void main(String[] a) throws Exception {
        Session.open(new File(a[0]),new File(a[1]));
        Properties plan=new Properties();
        try(java.io.Reader r=Files.newBufferedReader(new File(a[2]).toPath())){plan.load(r);}
        int zone=Integer.parseInt(plan.getProperty("island.zone"));
        ZO zo=new ZO(Workspace.getWorkspaceFile(ArchiveType.ZONE_DATA,zone),Workspace.session());
        ZoneHeader hdr=new ZoneHeader(zo.getFile(0),ctrmap.gamedef.GameType.ORAS);
        MapMatrix mm=new MapMatrix(new MM(Workspace.getWorkspaceFile(ArchiveType.MAP_MATRIX,hdr.mapmatrixID),Workspace.session()),Workspace.session());
        int[] regions=new int[8];
        for(int y=0;y<2;y++)for(int x=0;x<4;x++)regions[y*4+x]=mm.ids.get(x,y);
        System.out.println("source regions "+Arrays.toString(regions));
        IslandLandscape.remember(regions);
        IslandLandscape.placements=Files.readAllLines(new File(a[3]).toPath());
        List<String> rows=Files.readAllLines(new File(plan.getProperty("island.grid")).toPath());
        List<FrontierIsland.Building> buildings=new ArrayList<>();
        for(int i=0;plan.getProperty("island.building."+i)!=null;i++){
            String[] b=plan.getProperty("island.building."+i).split("\\|");
            buildings.add(new FrontierIsland.Building(b[0],Integer.parseInt(b[1]),Integer.parseInt(b[2]),Integer.parseInt(b[3]),Integer.parseInt(b[4]),!(b.length>5&&b[5].equals("nopassengers"))));
        }
        String[] c=plan.getProperty("island.clerk").split(",");
        System.out.println(FrontierIsland.build(zone,rows,buildings,new int[]{Integer.parseInt(c[0]),Integer.parseInt(c[1]),Integer.parseInt(c[2])}));
        mm=new MapMatrix(new MM(Workspace.getWorkspaceFile(ArchiveType.MAP_MATRIX,hdr.mapmatrixID),Workspace.session()),Workspace.session());
        for(int y=0;y<2;y++)for(int x=0;x<4;x++)regions[y*4+x]=mm.ids.get(x,y);
        System.out.println("landscape regions "+Arrays.toString(regions));
        System.out.println("pack "+Workspace.packArchives((p,w)->{}));
        System.out.println(FrontierPlaza.keepWorldTexturesInWorldPack(zone));
        System.out.println("pack "+Workspace.packArchives((p,w)->{}));
        System.out.println("outside the world pack: "+FrontierPlaza.worldTexturesOutsideWorldPack(zone));
        System.out.println(FrontierPlaza.loadBudget(zone));
    }
}
