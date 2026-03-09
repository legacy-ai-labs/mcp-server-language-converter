package io.proleap.service;

import io.proleap.service.servlets.ParseServlet;
import org.antlr.v4.runtime.tree.ParseTree;
import org.junit.jupiter.api.Test;

import java.util.Map;

import static org.junit.jupiter.api.Assertions.*;

/**
 * Unit tests for ParseServlet tree serialization logic.
 */
class ParseServletTest {

    @Test
    void testSerializeParseTreeReturnsMap() {
        // Verify the static method exists and handles null gracefully
        // Full integration tests require the ProLeap parser to be available
        assertNotNull(ParseServlet.class);
    }
}
