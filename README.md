# WebHawk — Advanced Python Excellenteam Final Project
WebHawk is a security middleware platform: every incoming request is checked for
SQL injection, XSS, and rate-limit abuse before it is forwarded to the real
backend it protects.


---
 
## Team
 
| Name | ID | Email |
|---|---|---|
| Benny Beer | 312556657 | bennybe@edu.jmc.ac.il |
| Nadav Ben Melech | 211728316 | nadavbenm@edu.jmc.ac.il |
| Orel Zabriko | 211845458 | orelzab@edu.jmc.ac.il |
 
---
 
## Services
 
| Compose service | Source folder | Host port | Role |
|---|---|---|---|
| `middleware` | `middleware/` | **8080** | Public entry point. All protected traffic. |
| `security-engine` | `services/security-engine/` | 8081 | SQLi / XSS / rate-limit detection. |
| `users-service` | `services/users/` | 8082 | Registration, login, JWT issue and revoke. |
| `backend-registry` | `services/backend_registry/` | 8083 | Backend registration and API key issuance. |
| `postgres` | — | 5432 | Shared database. |

---