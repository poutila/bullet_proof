# ADR-[NUMBER]: [Short Title]

**Date**: YYYY-MM-DD  
**Status**: [Proposed | Accepted | Deprecated | Superseded]  
**Deciders**: [List of people involved in decision]  
**Categories**: [Architecture | Security | Performance | Process]  

## 📚 Related Documentation
- **Standards**: [CLAUDE.md](../../CLAUDE.md)
- **Architecture**: [Architecture Overview](../architecture/README.md)
- **Planning**: [PLANNING.md](../../planning/PLANNING.md)

## Context and Problem Statement

[Describe the context and problem that needs to be addressed. Why is this decision necessary?]

### Background
[Provide any relevant background information, constraints, or requirements]

### Requirements
- [Requirement 1]
- [Requirement 2]
- [Requirement 3]

## Decision Drivers

- **Driver 1**: [e.g., Security requirements from CLAUDE.md]
- **Driver 2**: [e.g., Performance targets]
- **Driver 3**: [e.g., Maintainability]
- **Driver 4**: [e.g., Cost considerations]

## Considered Options

### Option 1: [Option Name]
**Description**: [Brief description]

**Pros**:
- [Advantage 1]
- [Advantage 2]

**Cons**:
- [Disadvantage 1]
- [Disadvantage 2]

### Option 2: [Option Name]
**Description**: [Brief description]

**Pros**:
- [Advantage 1]
- [Advantage 2]

**Cons**:
- [Disadvantage 1]
- [Disadvantage 2]

### Option 3: [Option Name]
**Description**: [Brief description]

**Pros**:
- [Advantage 1]
- [Advantage 2]

**Cons**:
- [Disadvantage 1]
- [Disadvantage 2]

## Decision Outcome

**Chosen option**: "[Option X]", because [justification].

### Implementation Details
[Describe how this will be implemented]

### Migration Strategy
[If replacing existing solution, describe migration approach]

## Consequences

### Positive
- [Good consequence 1]
- [Good consequence 2]
- [Good consequence 3]

### Negative
- [Negative consequence 1]
- [Negative consequence 2]

### Neutral
- [Neutral consequence 1]
- [Neutral consequence 2]

## Compliance

### Security Compliance
- [ ] Follows security requirements in [CLAUDE.md](../../CLAUDE.md)
- [ ] No hardcoded secrets or sensitive data
- [ ] Input validation implemented
- [ ] Rate limiting considered

### Development Standards
- [ ] Follows SOLID principles
- [ ] Test coverage plan defined
- [ ] Documentation requirements met
- [ ] Performance targets achievable

## Links and References

- [Link to relevant documentation]
- [Link to related ADRs]
- [External references]

## Notes

[Any additional notes, future considerations, or open questions]

---

### ADR Template Instructions (Remove when creating actual ADR)

1. **Number**: Use next sequential number (check existing ADRs)
2. **Title**: Keep short and descriptive
3. **Status**: 
   - Proposed: Under discussion
   - Accepted: Decision made
   - Deprecated: No longer relevant
   - Superseded: Replaced by another ADR
4. **Deciders**: Include all stakeholders
5. **Options**: Include at least 3 options (including "do nothing")
6. **Decision**: Clear rationale linking back to requirements
7. **Consequences**: Be honest about trade-offs

Example filename: `ADR-001-use-python-fastapi.md`