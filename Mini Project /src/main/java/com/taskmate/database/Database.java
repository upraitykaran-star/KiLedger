package com.taskmate.database;

import com.taskmate.config.DatabaseConfig;
import java.sql.*;

public final class Database {
    private Database() {}
    public static Connection connect() throws SQLException {
        try { DatabaseConfig cfg=DatabaseConfig.load(); return DriverManager.getConnection(cfg.url(), cfg.user(), cfg.password()); }
        catch (java.io.IOException e) { throw new SQLException(e.getMessage(), e); }
    }
    public static String diagnose(SQLException e) {
        String m=e.getMessage()==null?"":e.getMessage().toLowerCase();
        if (m.contains("communications link failure") || m.contains("connection refused") || m.contains("connect timed out")) return "Cannot reach MySQL. Start the MySQL 8 service, then retry.";
        if (m.contains("unknown database")) return "Database taskmate_db was not found. Run: mysql -u root -p < database/schema.sql";
        if (m.contains("access denied")) return "MySQL rejected the configured username/password. Check taskmate.properties.";
        if (m.contains("doesn't exist") || m.contains("does not exist")) return "TaskMate tables are missing. Run database/schema.sql before launching.";
        return "Database error: " + e.getMessage();
    }
}
