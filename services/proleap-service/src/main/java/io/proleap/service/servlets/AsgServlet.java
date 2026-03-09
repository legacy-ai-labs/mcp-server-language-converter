package io.proleap.service.servlets;

import com.google.gson.Gson;
import com.google.gson.JsonObject;
import io.proleap.cobol.asg.metamodel.*;
import io.proleap.cobol.asg.metamodel.data.DataDivision;
import io.proleap.cobol.asg.metamodel.data.datadescription.DataDescriptionEntry;
import io.proleap.cobol.asg.metamodel.data.workingstorage.WorkingStorageSection;
import io.proleap.cobol.asg.metamodel.environment.EnvironmentDivision;
import io.proleap.cobol.asg.metamodel.identification.IdentificationDivision;
import io.proleap.cobol.asg.metamodel.identification.ProgramIdParagraph;
import io.proleap.cobol.asg.metamodel.procedure.ProcedureDivision;
import io.proleap.cobol.asg.metamodel.procedure.Paragraph;
import io.proleap.cobol.asg.metamodel.procedure.Section;
import io.proleap.cobol.asg.metamodel.procedure.Statement;
import io.proleap.cobol.asg.runner.impl.CobolParserRunnerImpl;
import io.proleap.cobol.preprocessor.CobolPreprocessor.CobolSourceFormatEnum;
import jakarta.servlet.http.HttpServlet;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.io.*;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.util.*;

/**
 * Build ASG (Abstract Semantic Graph) from COBOL source.
 * POST /v1/cobol/asg/text
 *
 * Uses proleap-cobol-parser (MIT licensed) for full ASG construction.
 */
public class AsgServlet extends HttpServlet {

    private static final Logger LOG = LoggerFactory.getLogger(AsgServlet.class);
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
            CobolSourceFormatEnum sourceFormat = ParseServlet.parseFormat(format);
            tempFile = writeTempCobolFile(code, format);

            CobolParserRunnerImpl runner = new CobolParserRunnerImpl();
            Program program = runner.analyzeFile(tempFile, sourceFormat);

            Map<String, Object> asg = serializeProgram(program);

            Map<String, Object> result = new LinkedHashMap<>();
            result.put("success", true);
            result.put("asg", asg);
            result.put("format", format);

            resp.setStatus(HttpServletResponse.SC_OK);
            resp.getWriter().write(GSON.toJson(result));

        } catch (Exception e) {
            LOG.error("ASG build error", e);
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

    private File writeTempCobolFile(String code, String format) throws IOException {
        String suffix = "FIXED".equalsIgnoreCase(format) ? ".cbl" : ".cob";
        File tempFile = Files.createTempFile("proleap-asg-", suffix).toFile();
        try (Writer writer = new FileWriter(tempFile, StandardCharsets.UTF_8)) {
            writer.write(code);
        }
        return tempFile;
    }

    private Map<String, Object> serializeProgram(Program program) {
        Map<String, Object> result = new LinkedHashMap<>();

        List<Map<String, Object>> compilationUnits = new ArrayList<>();
        for (CompilationUnit cu : program.getCompilationUnits()) {
            compilationUnits.add(serializeCompilationUnit(cu));
        }
        result.put("compilation_units", compilationUnits);
        return result;
    }

    private Map<String, Object> serializeCompilationUnit(CompilationUnit cu) {
        Map<String, Object> result = new LinkedHashMap<>();

        ProgramUnit programUnit = cu.getProgramUnit();
        if (programUnit != null) {
            result.put("program_unit", serializeProgramUnit(programUnit));
        }

        return result;
    }

    private Map<String, Object> serializeProgramUnit(ProgramUnit pu) {
        Map<String, Object> result = new LinkedHashMap<>();

        // Identification Division
        IdentificationDivision idDiv = pu.getIdentificationDivision();
        if (idDiv != null) {
            Map<String, Object> idMap = new LinkedHashMap<>();
            ProgramIdParagraph pid = idDiv.getProgramIdParagraph();
            if (pid != null) {
                idMap.put("program_id", pid.getName());
            }
            result.put("identification_division", idMap);
        }

        // Environment Division
        EnvironmentDivision envDiv = pu.getEnvironmentDivision();
        if (envDiv != null) {
            Map<String, Object> envMap = new LinkedHashMap<>();
            envMap.put("present", true);
            result.put("environment_division", envMap);
        }

        // Data Division
        DataDivision dataDiv = pu.getDataDivision();
        if (dataDiv != null) {
            result.put("data_division", serializeDataDivision(dataDiv));
        }

        // Procedure Division
        ProcedureDivision procDiv = pu.getProcedureDivision();
        if (procDiv != null) {
            result.put("procedure_division", serializeProcedureDivision(procDiv));
        }

        return result;
    }

    private Map<String, Object> serializeDataDivision(DataDivision dataDiv) {
        Map<String, Object> result = new LinkedHashMap<>();

        WorkingStorageSection ws = dataDiv.getWorkingStorageSection();
        if (ws != null) {
            List<Map<String, Object>> items = new ArrayList<>();
            for (DataDescriptionEntry entry : ws.getDataDescriptionEntries()) {
                items.add(serializeDataDescriptionEntry(entry));
            }
            result.put("working_storage_section", Map.of("data_items", items));
        }

        return result;
    }

    private Map<String, Object> serializeDataDescriptionEntry(DataDescriptionEntry entry) {
        Map<String, Object> item = new LinkedHashMap<>();
        item.put("level_number", entry.getLevelNumber());
        if (entry.getName() != null) {
            item.put("name", entry.getName());
        }
        item.put("type", entry.getDataDescriptionEntryType().toString());
        return item;
    }

    private Map<String, Object> serializeProcedureDivision(ProcedureDivision procDiv) {
        Map<String, Object> result = new LinkedHashMap<>();

        // Sections
        List<Map<String, Object>> sections = new ArrayList<>();
        for (Section section : procDiv.getSections()) {
            Map<String, Object> secMap = new LinkedHashMap<>();
            secMap.put("name", section.getName());

            List<Map<String, Object>> paragraphs = new ArrayList<>();
            for (Paragraph para : section.getParagraphs()) {
                paragraphs.add(serializeParagraph(para));
            }
            secMap.put("paragraphs", paragraphs);
            sections.add(secMap);
        }
        result.put("sections", sections);

        // Top-level paragraphs (not in sections)
        List<Map<String, Object>> paragraphs = new ArrayList<>();
        for (Paragraph para : procDiv.getParagraphs()) {
            paragraphs.add(serializeParagraph(para));
        }
        result.put("paragraphs", paragraphs);

        // Statements
        List<Map<String, Object>> statements = new ArrayList<>();
        for (Statement stmt : procDiv.getStatements()) {
            statements.add(serializeStatement(stmt));
        }
        result.put("statements", statements);

        return result;
    }

    private Map<String, Object> serializeParagraph(Paragraph para) {
        Map<String, Object> result = new LinkedHashMap<>();
        result.put("name", para.getName());

        List<Map<String, Object>> statements = new ArrayList<>();
        for (Statement stmt : para.getStatements()) {
            statements.add(serializeStatement(stmt));
        }
        result.put("statements", statements);
        return result;
    }

    private Map<String, Object> serializeStatement(Statement stmt) {
        Map<String, Object> result = new LinkedHashMap<>();
        result.put("type", stmt.getStatementType().toString());
        if (stmt.getCtx() != null && stmt.getCtx().getStart() != null) {
            result.put("line", stmt.getCtx().getStart().getLine());
        }
        return result;
    }
}
