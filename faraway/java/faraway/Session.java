package faraway;

import ctrmap.Workspace;
import ctrmap.WorkspaceSession;
import ctrmap.gamedef.ArchiveType;
import ctrmap.gamedef.GameProfile;
import ctrmap.gamedef.GameType;
import java.io.File;
import java.io.IOException;
import java.nio.file.Files;

/** Opens a CTRMap-F5 workspace over a staged copy of the game, the way its own headless builder does. */
final class Session {

	private Session() {
	}

	static WorkspaceSession open(File game, File ws) throws IOException {
		Workspace.reset();
		Workspace.GAMEDIR_PATH = game.getAbsolutePath();
		Workspace.WORKSPACE_PATH = ws.getAbsolutePath();
		ws.mkdirs();
		// Detection only checks that the sound archive exists; an empty stand-in is never shipped.
		File sound = new File(game, GameProfile.of(GameType.ORAS).archivePath(ArchiveType.SOUND_BCSAR));
		if (!sound.exists()) {
			sound.getParentFile().mkdirs();
			Files.write(sound.toPath(), new byte[0]);
		}
		WorkspaceSession session;
		try {
			session = WorkspaceSession.open(ws, game);
		} catch (WorkspaceSession.OpenFailed ex) {
			throw new IOException("game did not open: " + ex.problems(), ex);
		}
		session.prepareDirectories();
		Workspace.install(session);
		Workspace.snapshotOriginals();
		return session;
	}
}
