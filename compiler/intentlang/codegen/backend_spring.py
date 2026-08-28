"""Java Spring Boot backend generator (Maven project)."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING, Optional

from ..artifact import ArtifactSet
from ..diagnostics import Diagnostics
from ._util import java_str, resolve_model
from .base import Generator

if TYPE_CHECKING:  # pragma: no cover
    from .. import ir as I
    from ..compiler import CompileOptions

_JAVA_TYPES = {
    "string": "String", "text": "String", "email": "String",
    "password": "String", "url": "String", "phone": "String",
    "enum": "String", "date": "LocalDate", "datetime": "LocalDateTime",
    "int": "Integer", "integer": "Integer", "id": "Long", "float": "Double",
    "boolean": "Boolean", "bool": "Boolean", "money": "BigDecimal", "json": "String",
}


class SpringGenerator(Generator):
    name = "backend/spring"

    def validate_options(self, options: "CompileOptions") -> Optional[str]:
        if options.backend not in ("spring", "springboot", "java"):
            return "options.backend must be 'spring'"
        return None

    def generate(self, module: "I.ModuleIR", options: "CompileOptions",
                 artifacts: ArtifactSet, diags: Diagnostics) -> None:
        self.art = artifacts
        self.module = module
        self._pom(options.database)
        self._application()
        self._properties(options.database)
        for model in module.models:
            self._entity(model)
            self._repo(model)
        for api in module.apis:
            self._controller(api)

    # -- infra ---------------------------------------------------------------
    def _pom(self, db: str) -> None:
        driver = {"sqlite": "org.xerial:sqlite-jdbc:3.46.0.0",
                  "postgres": "org.postgresql:postgresql:42.7.3",
                  "mysql": "com.mysql:mysql-connector-j:8.4.0"}[db]
        pom = f"""<?xml version="1.0" encoding="UTF-8"?>
<project xmlns="http://maven.apache.org/POM/4.0.0"
         xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
         xsi:schemaLocation="http://maven.apache.org/POM/4.0.0 http://maven.apache.org/xsd/maven-4.0.0.xsd">
  <modelVersion>4.0.0</modelVersion>
  <parent>
    <groupId>org.springframework.boot</groupId>
    <artifactId>spring-boot-starter-parent</artifactId>
    <version>3.3.2</version>
    <relativePath/>
  </parent>
  <groupId>com.intentos</groupId>
  <artifactId>app</artifactId>
  <version>1.0.0</version>
  <properties><java.version>21</java.version></properties>
  <dependencies>
    <dependency>
      <groupId>org.springframework.boot</groupId>
      <artifactId>spring-boot-starter-web</artifactId>
    </dependency>
    <dependency>
      <groupId>org.springframework.boot</groupId>
      <artifactId>spring-boot-starter-data-jpa</artifactId>
    </dependency>
    <dependency>
      <groupId>org.springframework.boot</groupId>
      <artifactId>spring-boot-starter-validation</artifactId>
    </dependency>
    <dependency>
      <groupId>{driver.split(':')[0]}</groupId>
      <artifactId>{driver.split(':')[1]}</artifactId>
      <version>{driver.split(':')[2]}</version>
    </dependency>
  </dependencies>
  <build><plugins>
    <plugin>
      <groupId>org.springframework.boot</groupId>
      <artifactId>spring-boot-maven-plugin</artifactId>
    </plugin>
  </plugins></build>
</project>
"""
        self.art.add("backend/pom.xml", pom, self.name)

    def _application(self) -> None:
        self.art.add(
            "backend/src/main/java/com/intentos/Application.java",
            "package com.intentos;\n\n"
            "import org.springframework.boot.SpringApplication;\n"
            "import org.springframework.boot.autoconfigure.SpringBootApplication;\n\n"
            "@SpringBootApplication\n"
            "public class Application {\n"
            "  public static void main(String[] args) {\n"
            "    SpringApplication.run(Application.class, args);\n"
            "  }\n"
            "}\n", self.name,
        )

    def _properties(self, db: str) -> None:
        if db == "postgres":
            url = "jdbc:postgresql://localhost:5432/app"
        elif db == "mysql":
            url = "jdbc:mysql://localhost:3306/app"
        else:
            url = "jdbc:sqlite:./app.db"
        self.art.add(
            "backend/src/main/resources/application.properties",
            f"spring.datasource.url={url}\n"
            "spring.datasource.username=${DB_USER}\n"
            "spring.datasource.password=${DB_PASSWORD}\n"
            "spring.jpa.hibernate.ddl-auto=update\n"
            "server.port=${PORT:8000}\n", self.name,
        )

    # -- entities -----------------------------------------------------------
    def _entity(self, model: "I.Model") -> None:
        lines = [
            "package com.intentos.model;",
            "",
            "import jakarta.persistence.*;",
            "import java.math.BigDecimal;",
            "import java.time.LocalDate;",
            "import java.time.LocalDateTime;",
            "",
            "@Entity",
            f'@Table(name = "{model.table.lower()}")',
            f"public class {model.pascal} {{",
        ]
        for f in model.fields:
            jt = _JAVA_TYPES.get(f.ftype, "String")
            if f.primary:
                lines.append("  @Id")
                lines.append("  @GeneratedValue(strategy = GenerationType.IDENTITY)")
            lines.append(f"  @Column(name = \"{f.name.lower()}\"{', nullable = false' if f.required and not f.primary else ''}{', unique = true' if f.unique else ''})")
            lines.append(f"  private {jt} {f.name};")
            lines.append("")
        for f in model.fields:
            jt = _JAVA_TYPES.get(f.ftype, "String")
            lines.append(f"  public {jt} get{f.pascal}() {{ return {f.name}; }}")
            lines.append(f"  public void set{f.pascal}({jt} {f.name}) {{ this.{f.name} = {f.name}; }}")
            lines.append("")
        lines.append("}")
        lines.append("")
        self.art.add(f"backend/src/main/java/com/intentos/model/{model.pascal}.java",
                     "\n".join(lines), self.name)

    def _repo(self, model: "I.Model") -> None:
        self.art.add(
            f"backend/src/main/java/com/intentos/repo/{model.pascal}Repository.java",
            "package com.intentos.repo;\n\n"
            "import com.intentos.model." + model.pascal + ";\n"
            "import org.springframework.data.jpa.repository.JpaRepository;\n\n"
            f"public interface {model.pascal}Repository extends JpaRepository<{model.pascal}, Long> {{\n"
            "}\n", self.name,
        )

    # -- controllers ---------------------------------------------------------
    def _controller(self, api: "I.Api") -> None:
        model = resolve_model(self.module, api)
        lines = [
            "package com.intentos.controller;",
            "",
            "import com.intentos.model.*;",
            "import com.intentos.repo.*;",
            "import org.springframework.http.ResponseEntity;",
            "import org.springframework.web.bind.annotation.*;",
            "",
            "@RestController",
            f'@RequestMapping("{self._prefix(api.route)}")',
            f"public class {api.pascal}Controller {{",
        ]
        if model:
            lines.append(f"  private final {model.pascal}Repository repo;")
            lines.append(f"  public {api.pascal}Controller({model.pascal}Repository repo) {{ this.repo = repo; }}")
            lines.append("")
            verb = api.method
            if verb == "GET":
                lines.append("  @GetMapping")
                lines.append("  public Object list() { return repo.findAll(); }")
            elif verb in ("POST", "PUT", "PATCH"):
                lines.append(f"  @{verb.capitalize()}Mapping")
                lines.append(f"  public Object save(@RequestBody {model.pascal} entity) {{ return repo.save(entity); }}")
            elif verb == "DELETE":
                lines.append('  @DeleteMapping("/{id}")')
                lines.append("  public Object delete(@PathVariable Long id) { repo.deleteById(id); return java.util.Map.of(\"ok\", true); }")
        else:
            lines.append(f"  @{api.method.capitalize()}Mapping")
            lines.append('  public Object ping() { return java.util.Map.of("ok", true); }')
        lines.append("}")
        lines.append("")
        self.art.add(f"backend/src/main/java/com/intentos/controller/{api.pascal}Controller.java",
                     "\n".join(lines), self.name)

    @staticmethod
    def _prefix(route: str) -> str:
        m = re.match(r"^(/[^/{}]+)", route)
        return m.group(1) if m else "/api"
