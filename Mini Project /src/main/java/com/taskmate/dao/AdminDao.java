package com.taskmate.dao;
import com.taskmate.database.Database;import com.taskmate.models.User;import com.taskmate.security.PasswordHasher;import java.sql.*;
public class AdminDao {
 public void createUser(User actor,String name,String email,char[] password,String role,String department,String year,String section)throws SQLException{
  if(!actor.role().equals("HOD"))throw new SecurityException("Only HOD can manage accounts.");
  if(!role.equals("FACULTY")&&!role.equals("STUDENT"))throw new IllegalArgumentException("HOD accounts are created through the first-run utility.");
  if(name.isBlank()||!email.matches("(?i)^[A-Z0-9._%+-]+@[A-Z0-9.-]+\\.[A-Z]{2,}$")||password.length<10)throw new IllegalArgumentException("Enter a name, valid email, and password of at least 10 characters.");
  String q="INSERT INTO users(name,email,password_hash,role,department,academic_year,section) VALUES(?,?,?,?,?,?,?)";
  try(Connection c=Database.connect();PreparedStatement p=c.prepareStatement(q)){p.setString(1,name.trim());p.setString(2,email.trim().toLowerCase());p.setString(3,PasswordHasher.hash(password));p.setString(4,role);p.setString(5,department);p.setString(6,year.isBlank()?null:year);p.setString(7,section.isBlank()?null:section);p.executeUpdate();}
 }
 public void setActive(User actor,long id,boolean active)throws SQLException{if(!actor.role().equals("HOD"))throw new SecurityException("Only HOD can manage accounts.");try(Connection c=Database.connect();PreparedStatement p=c.prepareStatement("UPDATE users SET is_active=? WHERE id=? AND role<>'HOD'")){p.setBoolean(1,active);p.setLong(2,id);p.executeUpdate();}}
 public Object[][] users(User actor)throws SQLException{if(!actor.role().equals("HOD"))throw new SecurityException("Only HOD can view all accounts.");try(Connection c=Database.connect();PreparedStatement p=c.prepareStatement("SELECT id,name,email,role,department,academic_year,section,is_active FROM users WHERE role<>'HOD' ORDER BY role,name");ResultSet r=p.executeQuery()){java.util.ArrayList<Object[]> rows=new java.util.ArrayList<>();while(r.next())rows.add(new Object[]{r.getLong(1),r.getString(2),r.getString(3),r.getString(4),r.getString(5),r.getString(6),r.getString(7),r.getBoolean(8)});return rows.toArray(Object[][]::new);}}
}
