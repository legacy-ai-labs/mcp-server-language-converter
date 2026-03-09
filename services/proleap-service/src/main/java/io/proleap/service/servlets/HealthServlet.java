package io.proleap.service.servlets;

import com.google.gson.Gson;
import jakarta.servlet.http.HttpServlet;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;

import java.io.IOException;
import java.util.List;
import java.util.Map;

/**
 * Health check endpoint.
 * GET /v1/cobol/health
 */
public class HealthServlet extends HttpServlet {

    private static final Gson GSON = new Gson();

    @Override
    protected void doGet(HttpServletRequest req, HttpServletResponse resp) throws IOException {
        resp.setContentType("application/json");
        resp.setCharacterEncoding("UTF-8");
        resp.setStatus(HttpServletResponse.SC_OK);

        Map<String, Object> health = Map.of(
                "status", "ok",
                "version", "1.0.0",
                "capabilities", List.of("parse", "asg", "analyze", "transform", "execute")
        );

        resp.getWriter().write(GSON.toJson(health));
    }
}
