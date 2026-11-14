package ctrmap.tests;

import ctrmap.formats.h3d.BchMapModel;
import java.io.ByteArrayOutputStream;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.List;

/**
 * Frontier Island (F11-ISLA-CONSTRUCCION): lossless merge of a painted cell's flat floor tiles. The painter writes one
 * quad per tile (four vertices, triangles 0,2,1 / 1,2,3) with world-space UVs (x/72, z/72). Adjacent tiles of one mesh
 * at the same height whose four vertices carry the same bytes apart from position and UV (same normal, same baked
 * colour/AO, same everything else) draw exactly as one quad spanning them: the UVs are linear in x and z, and every
 * other attribute is constant across the rectangle. Greedy rectangles of such tiles are written as one quad each.
 * Tiles that differ in any other byte (an AO gradient at a wall, a shore) are left alone, so unlike the F11 lab's
 * CompactFloors no colour is interpolated across a merged quad. Tilemap and collision are not touched.
 * Derived from frontier/probes/island/CompactFloors.java (lab).
 */
public final class IslandFloors {

	private IslandFloors() {
	}

	static final int[] QUAD = {0, 2, 1, 1, 2, 3};

	static boolean near(float a, float b) {
		return Math.abs(a - b) < 0.0002f;
	}

	/** The compacted model, and per merged mesh a line in `log`. */
	public static byte[] compact(byte[] original, StringBuilder log) {
		byte[] current = original;
		int count = new BchMapModel(original).meshCount;
		for (int mi = 0; mi < count; mi++) {
			BchMapModel m = new BchMapModel(current);
			BchMapModel.MeshGeom g = m.geometry().get(mi);
			BchMapModel.MeshAttr uv = m.findAttr(mi, 4);
			if (!g.posOk || g.posType != 3 || uv == null || uv.type != 3 || g.vertexCount % 4 != 0) {
				continue;
			}
			int n = g.vertexCount / 4;
			int[] tris = m.getTriangles(mi);
			if (tris.length != n * 6) {
				continue;
			}
			boolean authored = true;
			for (int q = 0; q < n && authored; q++) {
				for (int k = 0; k < 6; k++) {
					if (tris[q * 6 + k] != q * 4 + QUAD[k]) {
						authored = false;
					}
				}
			}
			if (!authored) {
				continue;
			}
			float[][] p = m.getVertexPositions(mi);
			// each vertex's bytes with position and UV blanked: what must match for a merge to be lossless
			byte[][] rest = new byte[g.vertexCount][];
			for (int v = 0; v < g.vertexCount; v++) {
				rest[v] = Arrays.copyOfRange(current, g.vtxAbs + v * g.stride, g.vtxAbs + (v + 1) * g.stride);
				Arrays.fill(rest[v], g.posOffset, g.posOffset + 12, (byte) 0);
				Arrays.fill(rest[v], uv.offset, uv.offset + uv.size(), (byte) 0);
			}
			int[][] cells = new int[40][40];
			for (int[] row : cells) {
				Arrays.fill(row, -1);
			}
			int[] xs = new int[n], ys = new int[n];
			Arrays.fill(xs, -1);
			for (int q = 0; q < n; q++) {
				int b = q * 4;
				float x = p[b][0], y = p[b][1], z = p[b][2];
				int tx = Math.round((x + 360) / 18), ty = Math.round((z + 360) / 18);
				if (tx < 0 || tx >= 40 || ty < 0 || ty >= 40 || !near(x, tx * 18 - 360) || !near(z, ty * 18 - 360)) {
					continue;
				}
				boolean floor = true;
				for (int k = 0; k < 4; k++) {
					if (!near(p[b + k][0], x + (k % 2) * 18) || !near(p[b + k][1], y) || !near(p[b + k][2], z + (k / 2) * 18)) {
						floor = false;
					}
					int v = g.vtxAbs + (b + k) * g.stride + uv.offset;
					if (!near(ctrmap.util.LittleEndian.f32(current, v), p[b + k][0] / 72)
							|| !near(ctrmap.util.LittleEndian.f32(current, v + 4), p[b + k][2] / 72)) {
						floor = false;
					}
				}
				for (int k = 1; k < 4 && floor; k++) {
					floor = Arrays.equals(rest[b + k], rest[b]);   // no gradient inside the tile either
				}
				if (floor) {
					if (cells[ty][tx] != -1) {
						throw new IllegalStateException("overlapping floor tiles on mesh " + mi);
					}
					cells[ty][tx] = q;
					xs[q] = tx;
					ys[q] = ty;
				}
			}
			boolean[] used = new boolean[n];
			ByteArrayOutputStream vertices = new ByteArrayOutputStream();
			List<Integer> indices = new ArrayList<>();
			int output = 0, covered = 0, expected = 0;
			for (int q = 0; q < n; q++) {
				if (xs[q] >= 0) {
					expected++;
				}
			}
			for (int q = 0; q < n; q++) {
				if (used[q]) {
					continue;
				}
				int x = xs[q], y = ys[q], w = 1, h = 1;
				if (x >= 0) {
					while (x + w < 40 && matches(cells[y][x + w], used, p, rest, q)) {
						w++;
					}
					outer:
					while (y + h < 40) {
						for (int dx = 0; dx < w; dx++) {
							if (!matches(cells[y + h][x + dx], used, p, rest, q)) {
								break outer;
							}
						}
						h++;
					}
					for (int dy = 0; dy < h; dy++) {
						for (int dx = 0; dx < w; dx++) {
							used[cells[y + dy][x + dx]] = true;
							covered++;
						}
					}
				} else {
					used[q] = true;
				}
				int[] corners = x < 0 ? new int[]{q * 4, q * 4 + 1, q * 4 + 2, q * 4 + 3}
						: new int[]{q * 4, cells[y][x + w - 1] * 4 + 1, cells[y + h - 1][x] * 4 + 2, cells[y + h - 1][x + w - 1] * 4 + 3};
				for (int v : corners) {
					vertices.write(current, g.vtxAbs + v * g.stride, g.stride);
				}
				for (int k : QUAD) {
					indices.add(output * 4 + k);
				}
				output++;
			}
			if (covered != expected) {
				throw new IllegalStateException("floor coverage changed on mesh " + mi);
			}
			if (output < n) {
				current = m.setMeshGeometry(mi, vertices.toByteArray(), indices.stream().mapToInt(i -> i).toArray());
				List<String> errs = new BchMapModel(current).validate();
				if (!errs.isEmpty()) {
					throw new IllegalStateException("merged model failed validation: " + errs.get(0));
				}
				log.append(" mesh ").append(mi).append(' ').append(n).append("->").append(output);
			}
		}
		return current;
	}

	/** Tile q may join the rectangle started at `start`: unused, same height, same non-position/UV bytes. */
	static boolean matches(int q, boolean[] used, float[][] p, byte[][] rest, int start) {
		if (q < 0 || used[q] || !near(p[q * 4][1], p[start * 4][1])) {
			return false;
		}
		for (int k = 0; k < 4; k++) {
			if (!Arrays.equals(rest[q * 4 + k], rest[start * 4 + k])) {
				return false;
			}
		}
		return true;
	}
}
