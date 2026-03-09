package io.proleap.service.servlets;

import com.google.gson.Gson;
import com.google.gson.JsonObject;
import io.proleap.cobol.CobolParser;
import io.proleap.cobol.asg.metamodel.CompilationUnit;
import io.proleap.cobol.asg.metamodel.Program;
import io.proleap.cobol.asg.runner.impl.CobolParserRunnerImpl;
import io.proleap.cobol.preprocessor.CobolPreprocessor.CobolSourceFormatEnum;
import jakarta.servlet.http.HttpServlet;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import org.antlr.v4.runtime.ParserRuleContext;
import org.antlr.v4.runtime.tree.ParseTree;
import org.antlr.v4.runtime.tree.TerminalNode;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.io.*;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/**
 * Parse COBOL source to AST (ANTLR parse tree).
 * POST /v1/cobol/parse/text
 *
 * Uses only proleap-cobol-parser (MIT licensed).
 */
public class ParseServlet extends HttpServlet {

    private static final Logger LOG = LoggerFactory.getLogger(ParseServlet.class);
    private static final Gson GSON = new Gson();

    @Override
    protected void doPost(HttpServletRequest req, HttpServletResponse resp) throws IOException {
        resp.setContentType("application/json");
        resp.setCharacterEncoding("UTF-8");

        String body = new String(req.getInputStream().readAllBytes(), StandardCharsets.UTF_8);
        JsonObject input = GSON.fromJson(body, JsonObject.class);

        if (input == null || !input.has("code")) {
            resp.setStatus(HttpServletResponse.SC_BAD_REQUEST);
            resp.getWriter().write(GSON.toJson(Map.of(
                    "success", false,
                    "error", "Missing required field: code"
            )));
            return;
        }

        String code = input.get("code").getAsString();
        String format = input.has("format") ? input.get("format").getAsString() : "FIXED";

        File tempFile = null;
        try {
            CobolSourceFormatEnum sourceFormat = parseFormat(format);
            tempFile = writeTempCobolFile(code, format);

            CobolParserRunnerImpl runner = new CobolParserRunnerImpl();
            Program program = runner.analyzeFile(tempFile, sourceFormat);

            CompilationUnit compilationUnit = program.getCompilationUnits().get(0);
            ParserRuleContext ctx = compilationUnit.getCtx();

            Map<String, Object> parseTree = serializeParseTree(ctx);

            Map<String, Object> result = new LinkedHashMap<>();
            result.put("success", true);
            result.put("parse_tree", parseTree);
            result.put("format", format);

            resp.setStatus(HttpServletResponse.SC_OK);
            resp.getWriter().write(GSON.toJson(result));

        } catch (Exception e) {
            LOG.error("Parse error", e);
            resp.setStatus(HttpServletResponse.SC_INTERNAL_SERVER_ERROR);
            resp.getWriter().write(GSON.toJson(Map.of(
                    "success", false,
                    "error", e.getMessage() != null ? e.getMessage() : e.getClass().getSimpleName()
            )));
        } finally {
            if (tempFile != null) {
                tempFile.delete();
            }
        }
    }

    static CobolSourceFormatEnum parseFormat(String format) {
        return switch (format.toUpperCase()) {
            case "TANDEM" -> CobolSourceFormatEnum.TANDEM;
            case "VARIABLE" -> CobolSourceFormatEnum.VARIABLE;
            default -> CobolSourceFormatEnum.FIXED;
        };
    }

    private File writeTempCobolFile(String code, String format) throws IOException {
        String suffix = "FIXED".equalsIgnoreCase(format) ? ".cbl" : ".cob";
        File tempFile = Files.createTempFile("proleap-parse-", suffix).toFile();
        try (Writer writer = new FileWriter(tempFile, StandardCharsets.UTF_8)) {
            writer.write(code);
        }
        return tempFile;
    }

    /**
     * Recursively serialize an ANTLR parse tree to a Map structure.
     */
    static Map<String, Object> serializeParseTree(ParseTree tree) {
        Map<String, Object> node = new LinkedHashMap<>();

        if (tree instanceof TerminalNode terminal) {
            node.put("type", "terminal");
            node.put("text", terminal.getText());
            node.put("token_type", terminal.getSymbol().getType());
            node.put("line", terminal.getSymbol().getLine());
            node.put("column", terminal.getSymbol().getCharPositionInLine());
        } else if (tree instanceof ParserRuleContext ctx) {
            node.put("type", "rule");
            node.put("rule_name", CobolParser.ruleNames[ctx.getRuleIndex()]);
            node.put("rule_index", ctx.getRuleIndex());

            if (ctx.getStart() != null) {
                node.put("start_line", ctx.getStart().getLine());
                node.put("start_column", ctx.getStart().getCharPositionInLine());
            }
            if (ctx.getStop() != null) {
                node.put("stop_line", ctx.getStop().getLine());
                node.put("stop_column", ctx.getStop().getCharPositionInLine());
            }

            List<Map<String, Object>> children = new ArrayList<>();
            for (int i = 0; i < tree.getChildCount(); i++) {
                children.add(serializeParseTree(tree.getChild(i)));
            }
            if (!children.isEmpty()) {
                node.put("children", children);
            }
        }

        return node;
    }
}
