export interface paths {
    "/api/v1/capabilities": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Capabilities */
        get: operations["capabilities_api_v1_capabilities_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/fixtures": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Fixture Catalog */
        get: operations["fixture_catalog_api_v1_fixtures_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/fixtures/{sample_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Fixture View */
        get: operations["fixture_view_api_v1_fixtures__sample_id__get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/fixtures/{sample_id}/image": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Fixture Image */
        get: operations["fixture_image_api_v1_fixtures__sample_id__image_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/health": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Health */
        get: operations["health_api_v1_health_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/schemas": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Schemas */
        get: operations["schemas_api_v1_schemas_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
}
export type webhooks = Record<string, never>;
export interface components {
    schemas: {
        /** APIError */
        APIError: {
            /** Code */
            code: string;
            /** Message */
            message: string;
            /** Request Id */
            request_id: string;
        };
        /** Capabilities */
        Capabilities: {
            /** Features */
            features: {
                [key: string]: "implemented" | "fixture" | "planned" | "unavailable";
            };
            /**
             * Model Benchmark Status
             * @default not_measured
             * @constant
             */
            model_benchmark_status: "not_measured";
            /**
             * Ocr Ready
             * @default false
             * @constant
             */
            ocr_ready: false;
            /**
             * Provider Mode
             * @enum {string}
             */
            provider_mode: "unconfigured" | "fixture";
            /** Supported Schemas */
            supported_schemas: string[];
        };
        /** Confidence */
        Confidence: {
            /** Mapping Signals */
            mapping_signals?: {
                [key: string]: string | number | boolean;
            };
            /**
             * Method
             * @default unknown
             * @enum {string}
             */
            method: "unknown" | "simulated" | "heuristic" | "calibrated";
            /** Ocr Score */
            ocr_score?: number | null;
            /**
             * Policy Version
             * @default confidence-draft-1
             */
            policy_version: string;
            /** Reason Codes */
            reason_codes?: string[];
            /** Score */
            score?: number | null;
        };
        /** DraftApplicationData */
        DraftApplicationData: {
            /** Class Name */
            class_name?: string | null;
            /** Date Of Birth */
            date_of_birth?: string | null;
            /** Faculty */
            faculty?: string | null;
            /** Full Name */
            full_name?: string | null;
            /** Request Content */
            request_content?: string | null;
            /** Request Date */
            request_date?: string | null;
            /** Student Id */
            student_id?: string | null;
        };
        /** ErrorEnvelope */
        ErrorEnvelope: {
            error: components["schemas"]["APIError"];
        };
        /** ExtractionRun */
        ExtractionRun: {
            /** Document Id */
            document_id: string;
            /** Fields */
            fields: components["schemas"]["FieldPrediction"][];
            provenance: components["schemas"]["Provenance"];
            /** Run Id */
            run_id: string;
            /** Schema Version */
            schema_version: string;
            /** Spans */
            spans: components["schemas"]["OCRSpan"][];
            /**
             * Status
             * @enum {string}
             */
            status: "succeeded" | "failed" | "unavailable";
        };
        /** FieldPrediction */
        FieldPrediction: {
            confidence?: components["schemas"]["Confidence"];
            /** Evidence Span Ids */
            evidence_span_ids?: string[];
            /**
             * Evidence Status
             * @enum {string}
             */
            evidence_status: "available" | "unavailable" | "unknown";
            /**
             * Field Id
             * @enum {string}
             */
            field_id: "full_name" | "student_id" | "date_of_birth" | "class_name" | "faculty" | "request_content" | "request_date";
            /** Normalized Value */
            normalized_value: string | null;
            /**
             * Observation
             * @enum {string}
             */
            observation: "found" | "not_found" | "unreadable" | "unknown";
            /** Raw Value */
            raw_value: string | null;
        };
        /** FixtureCatalog */
        FixtureCatalog: {
            /**
             * Prediction Source
             * @default fixture
             * @constant
             */
            prediction_source: "fixture";
            /** Sample Ids */
            sample_ids: string[];
        };
        /** FixtureView */
        FixtureView: {
            draft: components["schemas"]["DraftApplicationData"];
            /** Image Url */
            image_url: string;
            /** Label */
            label: string;
            run: components["schemas"]["ExtractionRun"];
            /** Sample Id */
            sample_id: string;
            /** Validation Issues */
            validation_issues: components["schemas"]["ValidationIssue"][];
        };
        /** Health */
        Health: {
            /** App Version */
            app_version: string;
            /**
             * Status
             * @default ok
             * @constant
             */
            status: "ok";
        };
        /** OCRSpan */
        OCRSpan: {
            /**
             * Coordinate System
             * @default original_pixels_top_left
             * @constant
             */
            coordinate_system: "original_pixels_top_left";
            /** Image Height */
            image_height: number;
            /** Image Width */
            image_width: number;
            /** Ocr Score */
            ocr_score?: number | null;
            /** Page Index */
            page_index: number;
            /** Polygon */
            polygon?: components["schemas"]["Point"][] | null;
            /** Span Id */
            span_id: string;
            /** Text */
            text: string;
            /**
             * Transform
             * @default identity
             * @constant
             */
            transform: "identity";
        };
        /** Point */
        Point: {
            /** X */
            x: number;
            /** Y */
            y: number;
        };
        /** Provenance */
        Provenance: {
            /**
             * Data Origin
             * @enum {string}
             */
            data_origin: "synthetic" | "sample";
            /**
             * Prediction Source
             * @enum {string}
             */
            prediction_source: "fixture" | "model" | "unavailable";
        };
        /** SchemaInfo */
        SchemaInfo: {
            /** Document Type */
            document_type: string;
            /** Required Fields */
            required_fields: ("full_name" | "student_id" | "date_of_birth" | "class_name" | "faculty" | "request_content" | "request_date")[];
            /** Schema Version */
            schema_version: string;
            /**
             * Status
             * @default provisional
             * @constant
             */
            status: "provisional";
        };
        /** ValidationIssue */
        ValidationIssue: {
            /** Code */
            code: string;
            /**
             * Field Path
             * @enum {string}
             */
            field_path: "full_name" | "student_id" | "date_of_birth" | "class_name" | "faculty" | "request_content" | "request_date";
            /** Message */
            message: string;
            /**
             * Severity
             * @enum {string}
             */
            severity: "error" | "warning";
        };
    };
    responses: never;
    parameters: never;
    requestBodies: never;
    headers: never;
    pathItems: never;
}
export type $defs = Record<string, never>;
export interface operations {
    capabilities_api_v1_capabilities_get: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Capabilities"];
                };
            };
            /** @description Not Found */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Unprocessable Content */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Internal Server Error */
            500: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Service Unavailable */
            503: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
        };
    };
    fixture_catalog_api_v1_fixtures_get: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["FixtureCatalog"];
                };
            };
            /** @description Not Found */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Unprocessable Content */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Internal Server Error */
            500: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Service Unavailable */
            503: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
        };
    };
    fixture_view_api_v1_fixtures__sample_id__get: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                sample_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["FixtureView"];
                };
            };
            /** @description Not Found */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Unprocessable Content */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Internal Server Error */
            500: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Service Unavailable */
            503: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
        };
    };
    fixture_image_api_v1_fixtures__sample_id__image_get: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                sample_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content?: never;
            };
            /** @description Not Found */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Unprocessable Content */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Internal Server Error */
            500: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Service Unavailable */
            503: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
        };
    };
    health_api_v1_health_get: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["Health"];
                };
            };
            /** @description Not Found */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Unprocessable Content */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Internal Server Error */
            500: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Service Unavailable */
            503: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
        };
    };
    schemas_api_v1_schemas_get: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["SchemaInfo"][];
                };
            };
            /** @description Not Found */
            404: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Unprocessable Content */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Internal Server Error */
            500: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
            /** @description Service Unavailable */
            503: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ErrorEnvelope"];
                };
            };
        };
    };
}
