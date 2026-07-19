import re
from repositories.security_repository import SecurityRepository


def _collect_all_strings(node) -> list:
    """
    Recursively extracts all string values from a JSON object (dict/list/str),
    so every text field sent by the client can be scanned for attack patterns.
    """
    results = []
    if isinstance(node, str):
        results.append(node)
    elif isinstance(node, dict):
        for value in node.values():
            results.extend(_collect_all_strings(value))
    elif isinstance(node, list):
        for item in node:
            results.extend(_collect_all_strings(item))
    return results


class SecurityService:
    @staticmethod
    def detect_sqli(input_str: str) -> bool:
        """
        SQL Injection Detector:
        Scans input for known SQLi patterns and returns True if a SQLi pattern is detected.
        """
        if not input_str or not isinstance(input_str, str):
            return False
            
        lower = input_str.lower()
        
        # Known SQL injection patterns from the project spec
        patterns = [
            r"('\s*(or|and)\s+.*=.*--)",          # ' OR 1=1 --
            r"(union\s+(all\s+)?select)",          # UNION SELECT / UNION ALL SELECT
            r"(drop\s+table)",                      # DROP TABLE
            r"(;\s*(delete|drop|insert|update)\s)",# ; DELETE FROM / ; DROP ...
            r"('\s*;\s*--)",                       # '; --
            r"(\b(select|insert|update|delete)\b.*\b(from|into|set)\b)", # SELECT ... FROM
            r"(1\s*=\s*1)",                        # 1=1
            r"('\s*or\s+'.*'\s*=\s*')",          # ' or 'a'='a'
        ]
        
        for pattern in patterns:
            if re.search(pattern, lower):
                return True
                
        return False

    @staticmethod
    def detect_xss(input_str: str) -> bool:
        """
        Cross-Site Scripting (XSS) Detector:
        Scans input for script tags and dangerous event handlers and
        returns True if an XSS pattern is detected.
        """
        if not input_str or not isinstance(input_str, str):
            return False
            
        lower = input_str.lower()
        
        patterns = [
            r"(<\s*script.*?>)",                                # <script> tags
            r"(javascript\s*:)",                                # javascript: URI
            r"(on(load|error|click|mouseover|focus|blur)\s*=)", # Inline event handlers
            r"(<\s*iframe.*?>)",                                # <iframe> tags
            r"(<\s*object.*?>)",                                # <object> tags
        ]
        
        for pattern in patterns:
            if re.search(pattern, lower):
                return True
                
        return False

    @staticmethod
    def analyze_request(payload: dict) -> dict:
        """
        Main entry point for the security engine.
        Receives the full JSON payload, runs SQLi + XSS + rate limit checks,
        logs the result to logs_security, and returns a verdict dict.
        """
        endpoint = payload.get("endpoint", "")
        method   = payload.get("method", "")
        ip       = payload.get("ip", "")

        # Collect all string values from body, query_params, path_params
        all_texts = []
        all_texts.extend(_collect_all_strings(payload.get("query_params", {})))
        all_texts.extend(_collect_all_strings(payload.get("path_params", {})))
        all_texts.extend(_collect_all_strings(payload.get("body", {})))

        # --- Check 1: SQL Injection ---
        for text in all_texts:
            if SecurityService.detect_sqli(text):
                SecurityRepository.log_request(endpoint, method, "sqli", True, ip)
                return {"allowed": False, "attack_type": "sqli", "reason": "SQL injection pattern detected"}

        # --- Check 2: XSS ---
        for text in all_texts:
            if SecurityService.detect_xss(text):
                SecurityRepository.log_request(endpoint, method, "xss", True, ip)
                return {"allowed": False, "attack_type": "xss", "reason": "XSS pattern detected"}

        # --- Check 3: Rate Limiting ---
        # Track requests per IP per endpoint in a time window (1 minute, max 100 requests)
        is_blocked = SecurityRepository.update_and_check_rate_limit(endpoint, ip, 1, 100)
        if is_blocked:
            SecurityRepository.log_request(endpoint, method, "rate_limit", True, ip)
            return {"allowed": False, "attack_type": "rate_limit", "reason": "Rate limit exceeded for this IP"}

        # All checks passed — log as clean and allow
        SecurityRepository.log_request(endpoint, method, "", False, ip)
        return {"allowed": True}
