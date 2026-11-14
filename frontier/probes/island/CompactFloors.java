package faraway;

import ctrmap.formats.h3d.BchMapModel;
import java.io.ByteArrayOutputStream;
import java.util.*;

/** Lab-only greedy rectangles. Terrain/collision do not change; corner AO interpolates across a rectangle. */
public final class CompactFloors {
    static boolean near(float a,float b) { return Math.abs(a-b)<0.0002f; }
    public static byte[] compact(byte[] original) {
        byte[] current=original;
        int count=new BchMapModel(original).meshCount;
        for(int mi=0;mi<count;mi++) {
            BchMapModel m=new BchMapModel(current);
            BchMapModel.MeshGeom g=m.geometry().get(mi);
            BchMapModel.MeshAttr uv=m.findAttr(mi,4);
            if(!g.posOk || uv==null || uv.type!=3 || g.vertexCount%4!=0) continue;
            int n=g.vertexCount/4; int[] tris=m.getTriangles(mi);
            if(tris.length!=n*6) continue;
            boolean authored=true;
            for(int q=0;q<n;q++) for(int k=0;k<6;k++)
                if(tris[q*6+k]!=q*4+new int[]{0,2,1,1,2,3}[k]) authored=false;
            if(!authored) continue;
            float[][] p=m.getVertexPositions(mi);
            int[][] cells=new int[40][40]; for(int[] row:cells) Arrays.fill(row,-1);
            int[] xs=new int[n],ys=new int[n];Arrays.fill(xs,-1);
            for(int q=0;q<n;q++) {
                int b=q*4;float x=p[b][0],y=p[b][1],z=p[b][2];
                int tx=Math.round((x+360)/18),ty=Math.round((z+360)/18);
                if(tx<0||tx>=40||ty<0||ty>=40||!near(x,tx*18-360)||!near(z,ty*18-360))continue;
                boolean floor=true;
                for(int k=0;k<4;k++) {
                    if(!near(p[b+k][0],x+(k%2)*18)||!near(p[b+k][1],y)||!near(p[b+k][2],z+(k/2)*18))floor=false;
                    int v=g.vtxAbs+(b+k)*g.stride+uv.offset;
                    if(!near(ctrmap.util.LittleEndian.f32(current,v),p[b+k][0]/72)
                        ||!near(ctrmap.util.LittleEndian.f32(current,v+4),p[b+k][2]/72))floor=false;
                }
                if(floor) {
                    if(cells[ty][tx]!=-1)throw new IllegalStateException("overlapping floors on mesh "+mi);
                    cells[ty][tx]=q;xs[q]=tx;ys[q]=ty;
                }
            }
            boolean[] used=new boolean[n];ByteArrayOutputStream vertices=new ByteArrayOutputStream();
            List<Integer> indices=new ArrayList<>();int output=0,covered=0,expected=0;
            for(int q=0;q<n;q++)if(xs[q]>=0)expected++;
            for(int q=0;q<n;q++) {
                if(used[q])continue;
                int x=xs[q],y=ys[q],w=1,h=1;
                if(x>=0) {
                    while(x+w<40 && matches(cells[y][x+w],used,p,q))w++;
                    outer: while(y+h<40) {
                        for(int dx=0;dx<w;dx++) if(!matches(cells[y+h][x+dx],used,p,q))break outer;
                        h++;
                    }
                    for(int dy=0;dy<h;dy++)for(int dx=0;dx<w;dx++) {used[cells[y+dy][x+dx]]=true;covered++;}
                } else used[q]=true;
                int[] corners=x<0 ? new int[]{q*4,q*4+1,q*4+2,q*4+3} : new int[]{q*4,cells[y][x+w-1]*4+1,cells[y+h-1][x]*4+2,cells[y+h-1][x+w-1]*4+3};
                for(int v:corners)vertices.write(current,g.vtxAbs+v*g.stride,g.stride);
                for(int k:new int[]{0,2,1,1,2,3})indices.add(output*4+k);
                output++;
            }
            if(covered!=expected)throw new IllegalStateException("floor coverage changed");
            if(output<n) {
                current=m.setMeshGeometry(mi,vertices.toByteArray(),indices.stream().mapToInt(i->i).toArray());
                if(!new BchMapModel(current).validate().isEmpty())throw new IllegalStateException("invalid compact model");
                System.out.println("COMPACT mesh="+mi+" quads="+n+" -> "+output+" floor tiles="+covered);
            }
        }
        return current;
    }
    static boolean matches(int q,boolean[] used,float[][] p,int start) {
        return q>=0&&!used[q]&&near(p[q*4][1],p[start*4][1]);
    }
}
