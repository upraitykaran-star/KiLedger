package com.taskmate.services;
import com.taskmate.dao.TaskDao; import com.taskmate.models.*; import java.sql.SQLException; import java.time.LocalDate; import java.util.List;
public class TaskService {
    private final TaskDao dao=new TaskDao();
    public List<Task> tasks(User u)throws SQLException{return dao.tasks(u);} public List<String[]> courses(User u)throws SQLException{return dao.courses(u);} public List<String[]> submissionsForTask(User u,long id)throws SQLException{return dao.submissionsForTask(u,id);}
    public void create(User u,long course,String title,String desc,String type,LocalDate due,String priority,double marks)throws SQLException{if(due.isBefore(LocalDate.now()))throw new IllegalArgumentException("Deadline must be today or later.");dao.createTask(u,course,title,desc,type,due,priority,marks);}
    public void submit(User u,long id)throws SQLException{dao.submit(u,id);} public void evaluate(User u,long id,double marks,String feedback)throws SQLException{dao.evaluate(u,id,marks,feedback);}
    public String taskStatus(Task t){if(t.status().equals("EVALUATED"))return "Completed";if(t.status().equals("SUBMITTED"))return "Submitted";if(t.dueDate().isBefore(LocalDate.now()))return "Overdue";if(t.dueDate().equals(LocalDate.now()))return "Due today";return "Pending";}
}
