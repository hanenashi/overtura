package io.github.hanenashi.overtura;

/** Shell boundaries are explicit. User fields accept names, never expressions. */
public final class Commands {
    private Commands() {}

    public static String alias(String value) {
        String clean = value.trim();
        if (!clean.matches("[A-Za-z0-9][A-Za-z0-9_.-]{0,63}")) {
            throw new IllegalArgumentException("Enter an SSH alias such as my-node. Use letters, numbers, dots, underscores or hyphens.");
        }
        return clean;
    }

    public static String session(String value) {
        String clean = value.trim();
        if (!clean.matches("[A-Za-z0-9][A-Za-z0-9_-]{0,63}")) {
            throw new IllegalArgumentException("Use a session name of 1–64 letters, numbers, underscores or hyphens, starting with a letter or number.");
        }
        return clean;
    }

    static String quote(String value) {
        return "'" + value.replace("'", "'\\''") + "'";
    }

    public static String login(String host) {
        return "ssh -t -- " + quote(alias(host));
    }

    public static String remote(String host, String action, String name) {
        String command = "exec \"$HOME/.local/bin/overtura\" ";
        switch (action) {
            case "doctor": command += "doctor"; break;
            case "list": command += "session list"; break;
            case "create":
            case "attach": command += "session " + action + " " + quote(session(name)); break;
            default: throw new IllegalArgumentException("Unsupported session action.");
        }
        return login(host) + " " + quote(command);
    }

    /** Copyable equivalent of the background query for debugging in Termux. */
    public static String readOnlyQuery(String host, String operation) {
        String[] args = readOnlyArgs(host, operation);
        return "ssh -T -o BatchMode=yes -o ConnectTimeout=8 -o ServerAliveInterval=5"
            + " -o ServerAliveCountMax=2 -- " + quote(args[10]) + " " + quote(args[11]);
    }

    public static String termuxShellQuery(String host, String operation) {
        return "exec timeout -k 1s 18s " + readOnlyQuery(host, operation);
    }

    /** Structured equivalent of a read-only SSH query. */
    public static String[] readOnlyArgs(String host, String operation) {
        String remote;
        switch (operation) {
            case "capabilities": remote = "capabilities"; break;
            case "doctor": remote = "doctor"; break;
            case "session.list": remote = "session list"; break;
            default: throw new IllegalArgumentException("Unsupported read-only query.");
        }
        return new String[]{"-T", "-o", "BatchMode=yes", "-o", "ConnectTimeout=8",
            "-o", "ServerAliveInterval=5", "-o", "ServerAliveCountMax=2", "--",
            alias(host), "exec \"$HOME/.local/bin/overtura\" --json " + remote};
    }
}
