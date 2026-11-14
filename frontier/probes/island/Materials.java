package faraway;

import ctrmap.Workspace;
import ctrmap.formats.containers.AD;
import ctrmap.formats.h3d.*;
import ctrmap.formats.tilemap.*;
import ctrmap.gamedef.ArchiveType;
import java.io.File;
import java.util.*;

/** Read-only costs: encoded texels, world-pack delta from area 101, and cut vertex/index bytes. */
public final class Materials {
    static byte[] pack(int area, int sub) throws Exception {
        return new AD(Workspace.getWorkspaceFile(ArchiveType.AREA_DATA, area), Workspace.session()).getFile(sub);
    }
    static void measure(String label, int region, int area, Collection<String> textures, int geometry) throws Exception {
        byte[] source = pack(area, 11), target = pack(101, 11);
        Set<String> names = new TreeSet<>(textures);
        int texels = 0;
        Set<String> found = new TreeSet<>();
        for (BchTexturePack.Texture t : BchTexturePack.parse(source)) {
            if (names.contains(t.name)) { texels += t.data.length; found.add(t.name); }
        }
        if (!found.equals(names)) throw new IllegalStateException(label + " missing world textures " + names + "/" + found);
        String delta;
        try { delta = String.valueOf(BchTexturePack.importTextures(target, source, new ArrayList<>(names)).length - target.length); }
        catch (IllegalStateException ex) { delta = "CONFLICT: " + ex.getMessage(); }
        System.out.println(label + "\t" + region + "\t" + area + "\t" + geometry + "\t" + texels + "\t" + delta + "\t" + names);
    }
    public static void main(String[] a) throws Exception {
        Session.open(new File(a[0]), new File(a[1]));
        System.out.println("label\tregion\tarea\tcut vertex+index bytes\tencoded texels\tworld delta vs area101\ttextures");
        for (int region : new int[]{489,490,491,492}) {
            BchMapModel model = new BchMapModel(BuildingCatalog.pristineRegion(Workspace.session(),region).getFile(1));
            for (int mesh=0; mesh<model.meshes.size(); mesh++) {
                int mat=model.getMeshMaterialIndex(mesh);
                System.out.println("RETAIL " + region + " mesh=" + mesh + " material=" + model.getMaterialName(mat) + " textures=" + model.getMaterialTextureNames(mat));
            }
        }
        for (int mesh : new int[]{1,2,3,4,5,9,13}) {
            BchMapModel m = new BchMapModel(BuildingCatalog.pristineRegion(Workspace.session(),489).getFile(1));
            BchMapModel.MeshGeom g = m.geometry().get(mesh);
            measure("NATIVE_489_" + mesh,489,101,m.getMaterialTextureNames(m.getMeshMaterialIndex(mesh)),g.vertexCount*g.stride+m.getTriangles(mesh).length*2);
        }
        BchMapModel decoration = new BchMapModel(BuildingCatalog.pristineRegion(Workspace.session(),490).getFile(1));
        BchMapModel.MeshGeom dg = decoration.geometry().get(0);
        measure("NATIVE_490_0",490,101,decoration.getMaterialTextureNames(decoration.getMeshMaterialIndex(0)),dg.vertexCount*dg.stride+decoration.getTriangles(0).length*2);
        for (TilePalette brush : new TilePalette[]{TilePalette.PATH, TilePalette.GRASS, TilePalette.SAND, TilePalette.WATER, TilePalette.STAIRS_Z, TilePalette.WALKWAY}) {
            TerrainCatalog.Donor d = TerrainCatalog.donors().get(brush);
            measure(brush.name(), d.donorRegion, d.donorArea, TerrainCatalog.donorTextures(Workspace.session(),d), 0);
        }
        TerrainCatalog.Donor d = TerrainCatalog.cliffDonor();
        measure("CLIFF", d.donorRegion, d.donorArea, TerrainCatalog.donorTextures(Workspace.session(),d), 0);
        MapPrefab palm = BuildingCatalog.extract(Workspace.session(), ctrmap.tests.FrontierPlaza.entry("Palm tree")).withoutPassengers();
        Set<String> palmNames = new TreeSet<>(); int palmGeom=0;
        for (MapPrefab.Piece piece : palm.pieces) { palmNames.addAll(piece.textures); palmGeom += piece.vertexBytes.length + piece.triangles.length*2; }
        measure("Palm tree (no passengers)",465,85,palmNames,palmGeom);
        for (String name : new String[]{"Roadside tree", "Palm tree", "Bush", "Iron fence (4-tile run)", "Pokémon League structure (flower01)"}) {
            BuildingCatalog.Entry e = ctrmap.tests.FrontierPlaza.entry(name);
            MapPrefab p = BuildingCatalog.extract(Workspace.session(), e);
            if (p == null || p.pieces.isEmpty()) throw new IllegalStateException("Empty cut: " + name);
            Set<String> names = new TreeSet<>(); int geom = 0;
            for (MapPrefab.Piece piece : p.pieces) { names.addAll(piece.textures); geom += piece.vertexBytes.length + piece.triangles.length * 2; }
            measure(name,e.donorRegion,e.donorArea,names,geom);
        }
    }
}
