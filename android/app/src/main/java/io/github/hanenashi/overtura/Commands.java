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

    /** Future background diagnostics: read-only, no PTY, no password prompt. */
    public static String readOnlyQuery(String host, String operation) {
        String args;
        switch (operation) {
            case "capabilities": args = "capabilities"; break;
            case "doctor": args = "doctor"; break;
            case "session.list": args = "session list"; break;
            default: throw new IllegalArgumentException("Unsupported read-only query.");
        }
        return "ssh -T -o BatchMode=yes -o ConnectTimeout=8 -o ServerAliveInterval=5"
            + " -o ServerAliveCountMax=2 -- " + quote(alias(host)) + " "
            + quote("exec \"$HOME/.local/bin/overtura\" --json " + args);
    }
}
