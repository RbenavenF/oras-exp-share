package faraway;

import ctrmap.Workspace;
import ctrmap.formats.containers.AD;
import ctrmap.formats.containers.GR;
import ctrmap.formats.h3d.*;
import ctrmap.formats.h3d.texturing.TextureCodec;
import ctrmap.formats.tilemap.*;
import ctrmap.gamedef.ArchiveType;
import ctrmap.tests.FrontierPlaza;
import java.io.File;
import java.util.*;
import java.awt.image.BufferedImage;
import javax.imageio.ImageIO;

/** Read-only material audit and retail texture export, not an art generator.
 * GAME WS REGION OUTDIR. REGION is the actual source cell printed by LandscapeTrial.
 */
public final class LandscapeAudit {
    private static void texture(int area, Set<String> names, File out) throws Exception {
        AD ad=new AD(Workspace.getWorkspaceFile(ArchiveType.AREA_DATA,area),Workspace.session());
        for(BchTexturePack.Texture t:BchTexturePack.parse(ad.getFile(11))) if(names.contains(t.name)) {
            System.out.println("area="+area+" texture="+t.name+" size="+t.getWidth()+"x"+t.getHeight()+" bytes="+t.data.length);
            byte[] rgba=TextureCodec.decode(t.data,t.getWidth(),t.getHeight(),PICACommandReader.TextureFormat.values()[t.format]);
            BufferedImage image=new BufferedImage(t.getWidth(),t.getHeight(),BufferedImage.TYPE_INT_ARGB);
            for(int y=0;y<t.getHeight();y++)for(int x=0;x<t.getWidth();x++){
                int i=(y*t.getWidth()+x)*4;
                image.setRGB(x,y,((rgba[i+3]&255)<<24)|((rgba[i]&255)<<16)|((rgba[i+1]&255)<<8)|(rgba[i+2]&255));
            }
            ImageIO.write(image,"png",new File(out,"tex-"+area+"-"+t.name+".png"));
        }
    }
    public static void main(String[] a) throws Exception {
        if(a.length!=4)throw new IllegalArgumentException("GAME WS REGION OUTDIR");
        Session.open(new File(a[0]),new File(a[1]));
        File out=new File(a[3]); out.mkdirs();
        BchMapModel m=new BchMapModel(new GR(Workspace.getWorkspaceFile(ArchiveType.FIELD_DATA,Integer.parseInt(a[2])),Workspace.session()).getFile(1));
        Set<String> names=new LinkedHashSet<>();
        for(TilePalette t:new TilePalette[]{TilePalette.STAIRS_Z,TilePalette.WATER,TilePalette.PATH,TilePalette.ROCK}){
            int mi=PaintedMaterials.resolvedGroundMesh(m,t);
            List<String> textures=m.getMaterialTextureNames(m.getMeshMaterialIndex(mi));
            names.addAll(textures);
            System.out.println(t+" mesh="+mi+" material="+m.getMaterialName(m.getMeshMaterialIndex(mi))+" textures="+textures+" uv="+Arrays.toString(PaintedMaterials.uvScaleOf(Workspace.session(),m,mi)));
        }
        texture(229,names,out);
        for(int i=0;i<m.meshCount;i++)System.out.println("mesh="+i+" vertices="+m.geometry().get(i).vertexCount+" material="+m.getMaterialName(m.getMeshMaterialIndex(i))+" textures="+m.getMaterialTextureNames(m.getMeshMaterialIndex(i)));
        for(int i=0;i<m.meshCount;i++) if(m.getMaterialTextureNames(m.getMeshMaterialIndex(i)).contains("chip_steps01")){
            BchMapModel.MeshGeom g=m.geometry().get(i);
            BchMapModel.MeshAttr uv=m.findAttr(i,4);
            System.out.println("stair candidate mesh="+i+" material="+m.getMaterialName(m.getMeshMaterialIndex(i))+" vertices="+g.vertexCount);
            if(uv!=null && uv.type==3)for(int v=0;v<Math.min(4,g.vertexCount);v++){
                int at=g.vtxAbs+v*g.stride+uv.offset;
                System.out.println("uv="+ctrmap.util.LittleEndian.f32(m.raw,at)+","+ctrmap.util.LittleEndian.f32(m.raw,at+4));
            }
        }
        for(String name:new String[]{"Team Aqua Hideout structure (flag_01)","Team Magma Hideout structure (flag)","Team Magma Hideout structure (flagB)","Team Magma Hideout structure (flagC) 2"}){
            BuildingCatalog.Entry e=FrontierPlaza.entry(name);
            MapPrefab p=BuildingCatalog.extract(Workspace.session(),e);
            BchMapModel model=new BchMapModel(p.donorModel);
            Set<String> flagTextures=new LinkedHashSet<>();
            for(MapPrefab.Piece piece:p.pieces)if(piece.material.toLowerCase(Locale.ROOT).contains("flag")){
                List<String> ts=model.getMaterialTextureNames(model.getMeshMaterialIndex(piece.donorMeshIndex));
                flagTextures.addAll(ts);
                System.out.println(name+" footprint="+e.tilesW()+"x"+e.tilesH()+" material="+piece.material+" vertexBytes="+piece.vertexBytes.length+" textures="+ts);
            }
            texture(e.donorArea,flagTextures,out);
        }
    }
}
