package com.taskmate.dao;
import com.taskmate.database.Database; import com.taskmate.models.User; import com.taskmate.security.PasswordHasher; import java.sql.*; import java.util.Optional;
public class AuthDao {
    public Optional<User> login(String email,char[] password) throws SQLException {
        String q="SELECT id,name,email,password_hash,role,department,academic_year,section FROM users WHERE email=? AND is_active=1";
        try(Connection c=Database.connect();PreparedStatement s=c.prepareStatement(q)){s.setString(1,email.trim().toLowerCase());try(ResultSet r=s.executeQuery()){if(!r.next()||!PasswordHasher.verify(password,r.getString("password_hash")))return Optional.empty();return Optional.of(new User(r.getLong("id"),r.getString("name"),r.getString("email"),r.getString("role"),r.getString("department"),r.getString("academic_year"),r.getString("section")));}}
    }
}
