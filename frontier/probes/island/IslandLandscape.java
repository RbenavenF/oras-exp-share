package ctrmap.tests;

import ctrmap.Workspace;
import ctrmap.formats.containers.GR;
import ctrmap.formats.h3d.BchMapModel;
import ctrmap.formats.h3d.BuildingCatalog;
import ctrmap.formats.h3d.BchModelAppender;
import ctrmap.formats.h3d.MapPrefab;
import ctrmap.formats.h3d.RegionFactory;
import ctrmap.formats.tilemap.PaintedMaterials;
import ctrmap.formats.tilemap.TilePalette;
import ctrmap.gamedef.ArchiveType;
import ctrmap.util.LittleEndian;
import java.util.*;

/** Isolated F11 landscape trial. Never stamps movement, collision, props or warps. */
public final class IslandLandscape {
    public static List<String> placements = Collections.emptyList();
    private static final Map<Integer, byte[][]> movement = new LinkedHashMap<>();

    public static void remember(int[] regions) throws Exception {
        movement.clear();
        if (regions.length != 8) throw new IllegalArgumentException("Eight production cells required");
        for (int i=0; i<8; i++) {
            GR gr = new GR(Workspace.getWorkspaceFile(ArchiveType.FIELD_DATA,regions[i]),Workspace.session());
            movement.put(i,new byte[][]{gr.getFile(0).clone(),gr.getFile(2).clone()});
        }
    }

    public static byte[] paving(byte[] donor) {
        BchMapModel m=new BchMapModel(donor);
        if(!m.getMaterialName(m.getMeshMaterialIndex(1)).equals("tokusane_miti"))
            throw new IllegalStateException("Re-audit Resort paving donor");
        return BchModelAppender.append(donor,donor,1,"road_island");
    }

    /** The reservation stays B in the source grid; only the visible covering changes. */
    public static TilePalette brush(char c, int x, int y) {
        if(c=='B') return x>=122 && x<=136 && y>=11 && y<=20 ? TilePalette.SAND : TilePalette.PATH;
        if(c=='f') return TilePalette.GRASS;
        if(c=='x') return TilePalette.PATH;
        switch(c) {
            case '~': case 'w': return TilePalette.WATER;
            case ',': case 'T': case 'p': return TilePalette.GRASS;
            case 's': return TilePalette.SAND;
            case '=': return TilePalette.STAIRS_Z;
            case '#': case 'o': return TilePalette.ROCK;
            default: return TilePalette.PATH;
        }
    }

    /** Restrict generated ramp UVs to the stone band in ORAS chip_steps01's atlas.
     * The original world projection wraps over its blank white area. Only UV bytes change.
     */
    public static void stairs(RegionFactory.BlankContent bc) {
        BchMapModel m = new BchMapModel(bc.model);
        int mi = PaintedMaterials.resolvedGroundMesh(m,TilePalette.STAIRS_Z);
        if(mi<0) return;
        if(!m.getMaterialTextureNames(m.getMeshMaterialIndex(mi)).contains("chip_steps01"))
            throw new IllegalStateException("Re-audit staircase atlas before changing its UVs");
        BchMapModel.MeshGeom g=m.geometry().get(mi);
        BchMapModel.MeshAttr uv=m.findAttr(mi,4);
        if(g.vertexCount <= 1) return;
        if(uv==null || uv.type!=3 || g.vertexCount%4!=0) throw new IllegalStateException("Expected painted stair quads");
        for(int v=0;v<g.vertexCount;v++) {
            int at=g.vtxAbs+v*g.stride+uv.offset;
            LittleEndian.putF32(bc.model,at,((v%4)%2==0 ? 65f : 126f)/128f);
            // TextureCodec's exported rows run opposite to the runtime sampler's V.
            LittleEndian.putF32(bc.model,at+4,1f-((v%4)/2==0 ? 98f : 125f)/128f);
        }
    }

    public static void preserve(RegionFactory.BlankContent bc,int cx,int cy) {
        byte[][] old=movement.get(cy*4+cx);
        if(old==null) throw new IllegalStateException("Missing production movement snapshot");
        bc.tilemap=old[0].clone(); bc.collision=old[1].clone();
    }

    private static void rotateAttribute(byte[] b,int at,int type) {
        if(type==3) {
            float x=LittleEndian.f32(b,at),z=LittleEndian.f32(b,at+8);
            LittleEndian.putF32(b,at,z); LittleEndian.putF32(b,at+8,-x);
        } else if(type==0) {
            byte x=b[at],z=b[at+2]; b[at]=z; b[at+2]=(byte)-x;
        } else throw new IllegalStateException("Re-audit rotated scenery attribute type "+type);
    }

    private static void transform(MapPrefab p,boolean rotate,boolean half,int width) {
        BchMapModel donor=new BchMapModel(p.donorModel);
        for(MapPrefab.Piece piece:p.pieces) for(int i=0;i<piece.vertexBytes.length;i+=piece.stride) {
            int at=i+piece.posOffset;
            float x=LittleEndian.f32(piece.vertexBytes,at),z=LittleEndian.f32(piece.vertexBytes,at+8);
            LittleEndian.putF32(piece.vertexBytes,at,half?x*.5f:z);
            LittleEndian.putF32(piece.vertexBytes,at+8,half?z*.5f:width-x);
            if(rotate) for(int semantic:new int[]{1,2}) {
                BchMapModel.MeshAttr a=donor.findAttr(piece.donorMeshIndex,semantic);
                if(a!=null) rotateAttribute(piece.vertexBytes,i+a.offset,a.type);
            }
        }
    }

    public static String decorate(RegionFactory.BlankContent bc,int cx,int cy,List<String> rows,
                                  Map<Integer,Set<String>> needs,List<String> placements) {
        StringBuilder out=new StringBuilder();
        for(String line:placements) {
            if(line.trim().isEmpty() || line.startsWith("#")) continue;
            String[] a=line.split("\\|");
            String name=a[0]; int x=Integer.parseInt(a[1]),y=Integer.parseInt(a[2]);
            if(x/40!=cx || y/40!=cy) continue;
            BuildingCatalog.Entry e=FrontierPlaza.entry(name);
            boolean horizontal=a.length>3 && a[3].equals("90");
            boolean half=a.length>3 && a[3].equals("half");
            int w=horizontal?e.tilesH():half?(e.tilesW()+1)/2:e.tilesW();
            int h=horizontal?e.tilesW():half?(e.tilesH()+1)/2:e.tilesH();
            if((x+w-1)/40!=cx || (y+h-1)/40!=cy) throw new IllegalStateException("Decoration crosses cell: "+line);
            MapPrefab p=BuildingCatalog.extract(Workspace.session(),e);
            // The generic passenger filter removes every chip_* mesh, including the scenery itself.
            // Keep only each measured retail scenery material, not ground, edges or shadow decals.
            p.pieces.removeIf(piece -> name.equals("Iron fence (4-tile run)")
                ? !piece.material.equals("chip_saku02") && !piece.material.equals("chip_saku02b")
                : name.equals("Team Aqua Hideout structure (flag_01)") ? !piece.material.equals("flag_01")
                : name.equals("Pokémon League structure (flower01)") ? !piece.material.equals("flower01")
                : !piece.material.equals("chip_wood_b"));
            if(horizontal || half) transform(p,horizontal,half,e.tilesW()*18);
            if(p.pieces.isEmpty()) throw new IllegalStateException("Empty scenery cut: "+line);
            int before=bc.model.length;
            float dy=(rows.get(80+y).charAt(x)-'0')*18f-e.baseY;
            MapPrefab.StampResult r=p.stampGeometry(bc.model,x%40,y%40,dy);
            if(!r.missingMaterials.isEmpty()) throw new IllegalStateException("Cannot stamp "+line+": "+r.missingMaterials);
            bc.model=r.newModel;
            needs.computeIfAbsent(e.donorArea,k->new LinkedHashSet<>()).addAll(r.texturesNeeded);
            out.append("landscape ").append(line).append(" model delta ").append(bc.model.length-before).append('\n');
        }
        return out.toString();
    }
}
