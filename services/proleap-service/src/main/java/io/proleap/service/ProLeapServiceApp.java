package io.proleap.service;

import io.proleap.cobol.servlets.cobol.analyze.CobolTextAnalyzeServlet;
import io.proleap.cobol.servlets.cobol.execute.CobolTextExecuteServlet;
import io.proleap.cobol.servlets.cobol.transform.CobolTextTransformServlet;
import io.proleap.service.servlets.AsgServlet;
import io.proleap.service.servlets.HealthServlet;
import io.proleap.service.servlets.ParseServlet;
import org.eclipse.jetty.server.Server;
import org.eclipse.jetty.servlet.ServletContextHandler;
import org.eclipse.jetty.servlet.ServletHolder;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

/**
 * ProLeap COBOL Service - HTTP sidecar for COBOL parsing, ASG, analysis,
 * transformation, and interpretation.
 *
 * <p>Runs an embedded Jetty server exposing REST endpoints that delegate to
 * ProLeap libraries. The MIT-licensed parser is used for /parse and /asg
 * routes; the AGPL-licensed modules power /analyze, /transform, and /execute.
 */
public class ProLeapServiceApp {

    private static final Logger LOG = LoggerFactory.getLogger(ProLeapServiceApp.class);
    private static final int DEFAULT_PORT = 4567;

    private final Server server;

    public ProLeapServiceApp(int port) {
        server = new Server(port);

        ServletContextHandler context = new ServletContextHandler(ServletContextHandler.NO_SESSIONS);
        context.setContextPath("/");
        server.setHandler(context);

        // Health check (custom)
        context.addServlet(new ServletHolder(new HealthServlet()), "/v1/cobol/health");

        // MIT-licensed routes (proleap-cobol-parser only)
        context.addServlet(new ServletHolder(new ParseServlet()), "/v1/cobol/parse/text");
        context.addServlet(new ServletHolder(new AsgServlet()), "/v1/cobol/asg/text");

        // AGPL-licensed routes (from proleap-cobol-app, using Micronaut DI)
        context.addServlet(CobolTextAnalyzeServlet.class, CobolTextAnalyzeServlet.PATTERN);
        context.addServlet(CobolTextTransformServlet.class, CobolTextTransformServlet.PATTERN);
        context.addServlet(CobolTextExecuteServlet.class, CobolTextExecuteServlet.PATTERN);
    }

    public void start() throws Exception {
        server.start();
        LOG.info("ProLeap COBOL Service started on port {}", ((org.eclipse.jetty.server.ServerConnector) server.getConnectors()[0]).getLocalPort());
    }

    public void stop() throws Exception {
        server.stop();
    }

    public void join() throws InterruptedException {
        server.join();
    }

    public int getPort() {
        return ((org.eclipse.jetty.server.ServerConnector) server.getConnectors()[0]).getLocalPort();
    }

    public boolean isRunning() {
        return server.isRunning();
    }

    public static void main(String[] args) throws Exception {
        int port = DEFAULT_PORT;
        if (args.length > 0) {
            try {
                port = Integer.parseInt(args[0]);
            } catch (NumberFormatException e) {
                LOG.warn("Invalid port '{}', using default {}", args[0], DEFAULT_PORT);
            }
        }

        String envPort = System.getenv("PROLEAP_PORT");
        if (envPort != null) {
            try {
                port = Integer.parseInt(envPort);
            } catch (NumberFormatException e) {
                LOG.warn("Invalid PROLEAP_PORT '{}', using {}", envPort, port);
            }
        }

        ProLeapServiceApp app = new ProLeapServiceApp(port);
        app.start();

        Runtime.getRuntime().addShutdownHook(new Thread(() -> {
            try {
                LOG.info("Shutting down ProLeap COBOL Service...");
                app.stop();
            } catch (Exception e) {
                LOG.error("Error during shutdown", e);
            }
        }));

        app.join();
    }
}
