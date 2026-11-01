using System;
using System.IO;
using SPICA.Formats.CtrH3D;

namespace MewModel
{
    public static class Program
    {
        public static int Main(string[] args)
        {
            // info FILE: list what a BCH holds
            if (args[0] == "info")
            {
                H3D h = H3D.Open(File.ReadAllBytes(args[1]));
                Console.WriteLine($"models {h.Models.Count} textures {h.Textures.Count} luts {h.LUTs.Count} materialAnims {h.MaterialAnimations.Count} skeletalAnims {h.SkeletalAnimations.Count}");
                foreach (var m in h.Models) Console.WriteLine($"model {m.Name} meshes {m.Meshes.Count} materials {m.Materials.Count} bones {m.Skeleton.Count}");
                foreach (var t in h.Textures) Console.WriteLine($"texture {t.Name} {t.Width}x{t.Height} {t.Format} mips {t.MipmapSize}");
                foreach (var m in h.Models)
                {
                    foreach (var mat in m.Materials)
                        Console.WriteLine($"material {mat.Name} shader '{mat.MaterialParams.ShaderReference}' tex '{mat.Texture0Name}' '{mat.Texture1Name}' '{mat.Texture2Name}' lut0 '{mat.MaterialParams.LUTDist0SamplerName}'");
                    foreach (var mesh in m.Meshes)
                        Console.WriteLine($"mesh mat {mesh.MaterialIndex} layer {mesh.Layer} priority {mesh.Priority} submeshes {mesh.SubMeshes.Count} attrs {mesh.Attributes.Count} stride {mesh.VertexStride}");
                }
                return 0;
            }
            // merge OUT IN1 IN2 ...: one BCH holding everything the inputs hold (model + textures)
            if (args[0] == "merge")
            {
                H3D scene = H3D.Open(File.ReadAllBytes(args[2]));
                for (int i = 3; i < args.Length; i++) scene.Merge(H3D.Open(File.ReadAllBytes(args[i])));
                H3D.Save(args[1], scene);
                H3D back = H3D.Open(File.ReadAllBytes(args[1]));
                Console.WriteLine($"wrote {args[1]}: models {back.Models.Count} textures {back.Textures.Count} luts {back.LUTs.Count}");
                return 0;
            }
            // fieldify OUT POKEMON_BCH TEXTURES_BCH FIELD_TEMPLATE_BCH
            // Battle Pokemon models use the PokePack shader, which the field never loads. Every material is
            // replaced by a copy of the template's first field material (FieldChar shader, combiners, LUTs),
            // keeping its name and taking the Pokemon's base colour texture ("...1") in the template's slot.
            if (args[0] == "fieldify")
            {
                H3D poke = H3D.Open(File.ReadAllBytes(args[2]));
                H3D textures = H3D.Open(File.ReadAllBytes(args[3]));
                byte[] templateBytes = File.ReadAllBytes(args[4]);
                H3D template = H3D.Open((byte[])templateBytes.Clone());
                var tmat = template.Models[0].Materials[0];
                var model = poke.Models[0];
                for (int i = 0; i < model.Materials.Count; i++)
                {
                    var old = model.Materials[i];
                    var copy = H3D.Open((byte[])templateBytes.Clone()).Models[0].Materials[0];   // Open relocates its buffer in place
                    copy.Name = old.Name;
                    copy.Texture1Name = old.Texture0Name;                      // Mew's "...1" diffuse map
                    model.Materials[i] = copy;
                    Console.WriteLine($"material {old.Name}: {old.MaterialParams.ShaderReference} -> {copy.MaterialParams.ShaderReference}, texture {copy.Texture1Name}");
                }
                // Battle models are larger than field characters: scale the skeleton's root bones.
                float scale = args.Length > 5 ? float.Parse(args[5], System.Globalization.CultureInfo.InvariantCulture) : 1f;
                foreach (var bone in model.Skeleton)
                {
                    if (bone.ParentIndex < 0)
                    {
                        bone.Scale *= scale;
                        Console.WriteLine($"root bone {bone.Name} scale {bone.Scale}");
                    }
                }
                poke.LUTs.Clear();
                foreach (var lut in template.LUTs) poke.LUTs.Add(lut);
                foreach (var t in textures.Textures)
                    if (t.Name.EndsWith("1")) poke.Textures.Add(t);
                foreach (var t in template.Textures)
                    if (t.Name == tmat.Texture0Name) poke.Textures.Add(t);
                H3D.Save(args[1], poke);
                H3D back = H3D.Open(File.ReadAllBytes(args[1]));
                Console.WriteLine($"wrote {args[1]}: materials {back.Models[0].Materials.Count} textures {back.Textures.Count} luts {back.LUTs.Count}");
                return 0;
            }
            // roundtrip IN OUT: open and save unchanged (writer check)
            if (args[0] == "roundtrip")
            {
                H3D.Save(args[2], H3D.Open(File.ReadAllBytes(args[1])));
                return 0;
            }
            return 1;
        }
    }
}
