package faraway;

import ctrmap.Workspace;
import ctrmap.formats.containers.GR;
import ctrmap.formats.h3d.BchMapModel;
import ctrmap.gamedef.ArchiveType;
import java.io.File;
import java.util.*;

/** Read-only byte proof for a stairs-UV-only follow-up. GAME_A WS_A GAME_B WS_B REGIONS_CSV.
 * Also compare the two mod manifests: only the FieldData archive may differ.
 */
public final class LandscapeUvProof {
    public static void main(String[] a) throws Exception {
        if(a.length!=5)throw new IllegalArgumentException("GAME_A WS_A GAME_B WS_B REGIONS_CSV");
        String[] ids=a[4].split(",");
        if(ids.length!=8)throw new IllegalArgumentException("Eight actual matrix regions required");
        Map<Integer,byte[][]> old=new LinkedHashMap<>();
        Session.open(new File(a[0]),new File(a[1]));
        for(String id:ids){
            int n=Integer.parseInt(id);
            GR gr=new GR(Workspace.getWorkspaceFile(ArchiveType.FIELD_DATA,n),Workspace.session());
            byte[][] files=new byte[7][];
            for(int s=0;s<7;s++)files[s]=gr.getFile(s).clone();
            old.put(n,files);
        }
        Session.open(new File(a[2]),new File(a[3]));
        int total=0;
        for(Map.Entry<Integer,byte[][]> cell:old.entrySet()){
            GR gr=new GR(Workspace.getWorkspaceFile(ArchiveType.FIELD_DATA,cell.getKey()),Workspace.session());
            for(int s=0;s<7;s++)if(s!=1 && !Arrays.equals(cell.getValue()[s],gr.getFile(s)))
                throw new IllegalStateException("Non-model change in GR"+cell.getKey()+"["+s+"]");
            byte[] before=cell.getValue()[1],after=gr.getFile(1);
            if(before.length!=after.length)throw new IllegalStateException("Model size changed");
            BchMapModel m=new BchMapModel(before);
            boolean[] allowed=new boolean[before.length];
            for(int i=0;i<m.meshCount;i++)if(m.getMaterialTextureNames(m.getMeshMaterialIndex(i)).contains("chip_steps01")){
                BchMapModel.MeshGeom g=m.geometry().get(i);
                BchMapModel.MeshAttr uv=m.findAttr(i,4);
                if(g.vertexCount<=1)continue;
                if(uv==null || uv.type!=3 || uv.elems!=2)throw new IllegalStateException("Unexpected UV format");
                for(int v=0;v<g.vertexCount;v++)Arrays.fill(allowed,g.vtxAbs+v*g.stride+uv.offset,g.vtxAbs+v*g.stride+uv.offset+8,true);
            }
            int changes=0;
            for(int j=0;j<before.length;j++)if(before[j]!=after[j]){
                if(!allowed[j])throw new IllegalStateException("Non-stair-UV byte changed in GR"+cell.getKey()+" at "+j);
                changes++;
            }
            total+=changes;
            System.out.println("GR"+cell.getKey()+": "+changes+" changed bytes, all within stair UVs");
        }
        if(total==0)throw new IllegalStateException("No UV changes found");
        System.out.println("UV_ONLY_OK "+total+" bytes; positions, normals, colors, commands and all other GR subfiles identical");
    }
}
