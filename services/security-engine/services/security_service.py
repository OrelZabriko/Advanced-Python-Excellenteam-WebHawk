import re

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
