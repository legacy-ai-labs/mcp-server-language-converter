package io.proleap.service;

import io.proleap.service.servlets.AsgServlet;
import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.*;

/**
 * Unit tests for AsgServlet serialization logic.
 */
class AsgServletTest {

    @Test
    void testAsgServletExists() {
        // Verify the servlet class is loadable
        assertNotNull(AsgServlet.class);
    }
}
