package faraway;

import ctrmap.Workspace;
import ctrmap.formats.containers.AD;
import ctrmap.formats.containers.GR;
import ctrmap.formats.containers.MM;
import ctrmap.formats.containers.ZO;
import ctrmap.formats.h3d.BchMapModel;
import ctrmap.formats.h3d.BchTexturePack;
import ctrmap.formats.h3d.PICACommandReader;
import ctrmap.formats.h3d.texturing.TextureCodec;
import ctrmap.formats.mapmatrix.MapMatrix;
import ctrmap.formats.zone.ZoneEntities;
import ctrmap.formats.zone.ZoneHeader;
import ctrmap.gamedef.ArchiveType;
import java.awt.Color;
import java.awt.Graphics2D;
import java.awt.Polygon;
import java.awt.RenderingHints;
import java.awt.image.BufferedImage;
import java.io.File;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

/**
 * F11-ISLA-CONSTRUCCION lab only: a top-down render of the island AS BUILT (not of the trace): every triangle of every
 * map cell's model (GR[1]) drawn from above, lowest first, filled with the average colour of its material's texture in
 * the area's world pack and shaded by height; door warps in red, NPCs in blue. Read-only on a built workspace.
 *   java faraway.TopView GAME WS ZONE OUT.png [PX_PER_TILE]
 */
public final class TopView {

	public static void main(String[] a) throws Exception {
		Session.open(new File(a[0]), new File(a[1]));
		int zone = Integer.parseInt(a[2]);
		int px = a.length > 4 ? Integer.parseInt(a[4]) : 8;
		ZO zo = new ZO(Workspace.getWorkspaceFile(ArchiveType.ZONE_DATA, zone), Workspace.session());
		ZoneHeader hdr = new ZoneHeader(zo.getFile(0), ctrmap.gamedef.GameType.ORAS);
		MapMatrix matrix = new MapMatrix(new MM(Workspace.getWorkspaceFile(ArchiveType.MAP_MATRIX, hdr.mapmatrixID),
				Workspace.session()), Workspace.session());
		AD ad = new AD(Workspace.getWorkspaceFile(ArchiveType.AREA_DATA, hdr.areadataID), Workspace.session());
		Map<String, Color> average = new HashMap<>();
		for (BchTexturePack.Texture t : BchTexturePack.parse(ad.getFile(11))) {
			try {
				byte[] rgba = TextureCodec.decode(t.data, t.getWidth(), t.getHeight(),
						PICACommandReader.TextureFormat.values()[t.format]);
				long r = 0, g = 0, b = 0, w = 0;
				for (int i = 0; i + 3 < rgba.length; i += 4) {
					int alpha = rgba[i + 3] & 0xff;
					r += (rgba[i] & 0xff) * alpha;
					g += (rgba[i + 1] & 0xff) * alpha;
					b += (rgba[i + 2] & 0xff) * alpha;
					w += alpha;
				}
				if (w > 0) {
					average.put(t.name, new Color((int) (r / w), (int) (g / w), (int) (b / w)));
				}
			} catch (RuntimeException undecoded) {
				// a format the codec does not read: grey below
			}
		}
		int W = matrix.width * 40, H = matrix.height * 40;
		BufferedImage img = new BufferedImage(W * px, H * px, BufferedImage.TYPE_INT_RGB);
		Graphics2D g = img.createGraphics();
		g.setRenderingHint(RenderingHints.KEY_ANTIALIASING, RenderingHints.VALUE_ANTIALIAS_OFF);
		g.setColor(Color.BLACK);
		g.fillRect(0, 0, img.getWidth(), img.getHeight());
		List<float[]> tris = new ArrayList<>();   // x0 z0 x1 z1 x2 z2 maxY rgb
		float lo = Float.MAX_VALUE, hi = -Float.MAX_VALUE;
		for (int cy = 0; cy < matrix.height; cy++) {
			for (int cx = 0; cx < matrix.width; cx++) {
				int region = matrix.ids.get(cx, cy);
				if (region == 0xFFFF) {
					continue;
				}
				BchMapModel m = new BchMapModel(new GR(Workspace.getWorkspaceFile(ArchiveType.FIELD_DATA, region),
						Workspace.session()).getFile(1));
				for (int mi = 0; mi < m.meshCount; mi++) {
					if (!m.geometry().get(mi).posOk) {
						continue;
					}
					List<String> names = m.getMaterialTextureNames(m.getMeshMaterialIndex(mi));
					Color c = names.isEmpty() ? null : average.get(names.get(0));
					if (c == null) {
						c = Color.GRAY;
					}
					float[][] p = m.getVertexPositions(mi);
					int[] t = m.getTriangles(mi);
					for (int k = 0; k + 2 < t.length; k += 3) {
						float[] tri = new float[8];
						float top = -Float.MAX_VALUE;
						for (int v = 0; v < 3; v++) {
							float[] q = p[t[k + v]];
							tri[v * 2] = (cx * 720 + q[0] + 360) / 18f * px;
							tri[v * 2 + 1] = (cy * 720 + q[2] + 360) / 18f * px;
							top = Math.max(top, q[1]);
						}
						tri[6] = top;
						tri[7] = c.getRGB();
						tris.add(tri);
						lo = Math.min(lo, top);
						hi = Math.max(hi, top);
					}
				}
			}
		}
		tris.sort((x, y) -> Float.compare(x[6], y[6]));
		for (float[] tri : tris) {
			Color c = new Color((int) tri[7]);
			float shade = 0.7f + 0.5f * (hi > lo ? (tri[6] - lo) / (hi - lo) : 0);
			g.setColor(new Color(Math.min(255, (int) (c.getRed() * shade)), Math.min(255, (int) (c.getGreen() * shade)),
					Math.min(255, (int) (c.getBlue() * shade))));
			Polygon poly = new Polygon(new int[]{Math.round(tri[0]), Math.round(tri[2]), Math.round(tri[4])},
					new int[]{Math.round(tri[1]), Math.round(tri[3]), Math.round(tri[5])}, 3);
			g.fillPolygon(poly);
		}
		ZoneEntities ent = new ZoneEntities(zo.getFile(1));
		g.setColor(Color.RED);
		for (ZoneEntities.Warp w : ent.warps) {
			g.fillRect((w.x - 9) / 18 * px, (w.y - 9) / 18 * px, px, px);
		}
		g.setColor(Color.BLUE);
		for (ZoneEntities.NPC n : ent.npcs) {
			g.fillRect(n.xTile * px, n.yTile * px, px, px);
		}
		g.dispose();
		javax.imageio.ImageIO.write(img, "png", new File(a[3]));
		System.out.println("top view " + a[3] + ": " + tris.size() + " triangles, " + ent.warps.size() + " warps, "
				+ ent.npcs.size() + " NPCs, heights " + lo + ".." + hi);
	}
}
