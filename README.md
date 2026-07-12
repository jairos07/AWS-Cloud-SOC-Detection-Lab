# AWS Cloud SOC Detection Lab — Detección y Respuesta a Incidentes en AWS

> **Laboratorio de Blue Team sobre AWS para detectar, alertar y responder automáticamente a actividad sospechosa en una cuenta, usando únicamente servicios nativos (sin agentes ni terceros).**

![Platform](https://img.shields.io/badge/Platform-AWS-orange)
![Purpose](https://img.shields.io/badge/⚠%20For-Educational%20Purposes%20Only-red)
![Language](https://img.shields.io/badge/Lambda-Python%203.12-blue)
![Focus](https://img.shields.io/badge/Focus-Blue%20Team%20%2F%20SOC-brightgreen)

---

## Descripción

Este repositorio documenta el despliegue completo de un **SOC en miniatura sobre AWS**: un pipeline de detección que audita la actividad de la cuenta con CloudTrail, dispara alarmas de CloudWatch ante eventos de riesgo, notifica por email vía SNS y registra cada incidente en DynamoDB mediante una función Lambda propia. El pipeline se valida provocando deliberadamente dos de los eventos detectados (creación de usuario y escalada de privilegios) y comprobando que las alarmas correspondientes se disparan.

---

## Arquitectura

```
 Llamadas a la API de AWS (IAM, EC2, etc.)
                 │
                 ▼
   CloudTrail · soc-management-trail (multi-región)
                 │  logs → S3 + CloudWatch Logs
                 ▼
   CloudWatch Logs · /aws/cloudtrail/soc-management-trail
                 │  6 Metric Filters (namespace SOCLab/Security)
                 ▼
   CloudWatch Alarms · SOC-*-ALARM
                 │
        ┌────────┴────────┐
        ▼                 ▼
   SNS · soc-security-alerts     Lambda · soc-incident-responder
        │                                 │
        ▼                                 ▼
     Email                       DynamoDB · soc-incidents
```

---

## Componentes desplegados

| Servicio | Recurso | Función |
|---|---|---|
| IAM | `soc-lab-admin`, `soc-lambda-responder-role` | Usuario administrador del lab y rol de ejecución de la Lambda |
| CloudTrail | `soc-management-trail` | Auditoría multi-región de todas las llamadas a la API |
| CloudWatch Logs | `/aws/cloudtrail/soc-management-trail` | Log group con 6 metric filters sobre eventos de CloudTrail |
| CloudWatch Alarms | 6× `SOC-*-ALARM` | Umbral por métrica → notificación + invocación Lambda |
| SNS | `soc-security-alerts` | Notificación por email al SOC |
| Lambda | `soc-incident-responder` (Python 3.12) | Normaliza la alarma, calcula severidad y persiste el incidente |
| DynamoDB | `soc-incidents` | Tabla de incidentes (`incident_id` + `timestamp`) |
| AWS Budgets | `soc-lab-zero-spend` | Alerta de coste ante cualquier gasto (> 0,01 $) |

---

## Detecciones implementadas

| Alarma | Evento CloudTrail | Umbral | Técnica MITRE ATT&CK |
|---|---|---|---|
| `SOC-FailedConsoleLogins-ALARM` | Login fallido en consola | ≥ 3 / 5 min | T1110.001 – Brute Force |
| `SOC-IAMUserCreation-ALARM` | `CreateUser` | ≥ 1 / 5 min | T1136.003 – Create Account: Cloud |
| `SOC-PrivilegeEscalation-ALARM` | `PutRolePolicy`, `AttachRolePolicy`, `AttachUserPolicy` | ≥ 1 / 5 min | T1098.001 – Additional Cloud Credentials |
| `SOC-CloudTrailTampering-ALARM` | `StopLogging`, `DeleteTrail`, `UpdateTrail` | ≥ 1 / 1 min | T1562.008 – Disable Cloud Logs |
| `SOC-AccessKeyCreation-ALARM` | `CreateAccessKey` | ≥ 1 / 5 min | T1098.001 – Additional Cloud Credentials |
| `SOC-RootAccountLogin-ALARM` | Login con cuenta root | ≥ 1 / 5 min | T1078.004 – Valid Accounts: Cloud |

Cada alarma dispara las mismas dos acciones: notificar a `soc-security-alerts` (SNS) e invocar `soc-incident-responder` (Lambda), que guarda el incidente en DynamoDB con severidad asignada (`LOW` a `CRITICAL` según el tipo de alarma).

---

## Validación del pipeline

Para comprobar la detección de extremo a extremo se simularon dos eventos reales:

| Acción simulada | Evento generado | Resultado |
|---|---|---|
| Creación del usuario `test-backdoor-user` | `CreateUser` | ✅ `SOC-IAMUserCreation-ALARM` → *In alarm* |
| Adjuntar `ReadOnlyAccess` al rol `soc-lambda-responder-role` | `AttachRolePolicy` | ✅ `SOC-PrivilegeEscalation-ALARM` → *In alarm* |

---

## Documentación completa

El despliegue paso a paso, con capturas de cada pantalla de la consola, está en [`DOCUMENTACION-TECNICA.md`](./DOCUMENTACION-TECNICA.md) / [`DOCUMENTACION-TECNICA.pdf`](./DOCUMENTACION-TECNICA.pdf). El código de la función Lambda está en [`src/lambda.py`](./src/lambda.py).

---

## Requisitos para reproducir el lab

- Una cuenta de AWS (capa gratuita es suficiente) con permisos de administrador.
- Servicios usados: IAM, CloudTrail, CloudWatch, SNS, Lambda, DynamoDB, Budgets — todos gestionados desde la consola web, sin infraestructura propia.
- Runtime **Python 3.12** para la función Lambda (dependencia única: `boto3`, incluida por defecto).

---

## Disclaimer

**Laboratorio exclusivamente educativo, desplegado en una cuenta de AWS propia y aislada.** Antes de compartir capturas de tu propio despliegue, difumina el Account ID y cualquier dato personal — ambos aparecen por defecto en casi cualquier pantalla de la consola.

---

## Autor

Proyecto desarrollado como parte de un portfolio de ciberseguridad defensiva (Blue Team / SOC) sobre infraestructura AWS propia.
