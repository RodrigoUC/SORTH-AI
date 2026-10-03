"""Optional local resource identities and explicit per-session membership.

No GUI preferences, storage, inferred identities, or automatic allocation live
here. Unknown availability does not constrain; declared windows are permissive
intervals whose union must cover a session. Intervals are half-open.
"""
from dataclasses import dataclass
from functools import cached_property
from types import MappingProxyType
import unicodedata


@dataclass(frozen=True)
class ResourceIssue:
    code: str
    entity_id: str = ''
    group_id: str = ''
    other_group_id: str = ''

    def __str__(self):
        return ': '.join(x for x in (self.code, self.entity_id, self.group_id,
                                    self.other_group_id) if x)

    def render(self, translate):
        source = {
            'TEACHER_OVERLAP': 'Docente {resource}: las sesiones {session} y {other} se solapan.',
            'STUDENT_GROUP_OVERLAP': 'Grupo de estudiantes {resource}: las sesiones {session} y {other} se solapan.',
            'STUDENT_OVERLAP': 'Estudiante {resource}: las sesiones {session} y {other} se solapan.',
            'OUTSIDE_DECLARED_AVAILABILITY': 'Recurso {resource}: la sesión {session} queda fuera de su disponibilidad declarada.',
        }.get(self.code)
        if source:
            return translate(source, resource=self.entity_id, session=self.group_id, other=self.other_group_id)
        return translate('Datos de recursos por corregir: {details}', details=str(self))


@dataclass(frozen=True)
class Resource:
    id: str
    label: str
    # None is unknown, () explicitly declares no permitted times.
    availability: tuple[tuple[int, int, int], ...] | None = None


@dataclass(frozen=True)
class ResourceCatalog:
    kind: str = 'teacher'
    enabled: bool = False
    resources: tuple[Resource, ...] = ()
    # An entry with None preserves an explicit unassigned choice. An absent
    # entry likewise imposes no constraint, without inventing a teacher.
    memberships: tuple[tuple[str, tuple[str, ...] | None], ...] = ()

    def __deepcopy__(self, memo):
        return self

    @cached_property
    def _members(self):
        return MappingProxyType(dict(self.memberships))

    @cached_property
    def _resources(self):
        return MappingProxyType({r.id: r for r in self.resources})

    def ids_for(self, group_id):
        return self._members.get(group_id) or ()

    def structure_issues(self, group_ids, time_model):
        issues, ids, sessions = [], set(), set()
        if self.kind not in RESOURCE_KINDS or type(self.enabled) is not bool:
            return [ResourceIssue('INVALID_RESOURCE_KIND')]
        for teacher in self.resources:
            if not _visible(teacher.id) or not _visible(teacher.label):
                issues.append(ResourceIssue('INVALID_RESOURCE', str(teacher.id)))
                continue
            if teacher.id in ids:
                issues.append(ResourceIssue('DUPLICATE_RESOURCE_ID', teacher.id))
            ids.add(teacher.id)
            if teacher.availability is not None:
                for window in teacher.availability:
                    if (not isinstance(window, (tuple, list)) or len(window) != 3
                            or any(type(x) is not int for x in window)
                            or window[0] not in time_model.index_to_day
                            or not 0 <= window[1] < window[2] <= 1440):
                        issues.append(ResourceIssue('INVALID_AVAILABILITY', teacher.id))
        for gid, tid in self.memberships:
            if gid in sessions:
                issues.append(ResourceIssue('DUPLICATE_SESSION_MEMBERSHIP', group_id=gid))
            sessions.add(gid)
            if gid not in group_ids:
                issues.append(ResourceIssue('UNKNOWN_SESSION_REFERENCE', group_id=gid))
            if tid is not None:
                if (not isinstance(tid, tuple) or len(set(tid)) != len(tid)
                        or (self.kind == 'teacher' and len(tid) > 1)):
                    issues.append(ResourceIssue('INVALID_MEMBERSHIP', group_id=gid))
                else:
                    for resource_id in tid:
                        if resource_id not in ids:
                            issues.append(ResourceIssue('UNKNOWN_RESOURCE_REFERENCE', resource_id, gid))
        return issues

    def placement_issues(self, group_id, day, start, end, assignments):
        """Single source for candidate admission and final independent validation."""
        issues = []
        if not self.enabled:
            return issues
        for tid in self.ids_for(group_id):
            teacher = self._resources.get(tid)
            if teacher is None:
                issues.append(ResourceIssue('UNKNOWN_RESOURCE_REFERENCE', tid, group_id))
                continue
            if teacher.availability is not None:
                covered = start
                for wd, ws, we in sorted(teacher.availability):
                    if wd == day and ws <= covered < we:
                        covered = we
                if covered < end:
                    issues.append(ResourceIssue('OUTSIDE_DECLARED_AVAILABILITY', tid, group_id))
            for other_id, placement in assignments.items():
                if other_id == group_id or tid not in self.ids_for(other_id):
                    continue
                if (not isinstance(placement, (list, tuple)) or len(placement) != 4
                        or any(type(v) is not int for v in placement[1:])):
                    continue
                _, od, os, oe = placement
                if day == od and start < oe and end > os:
                    issues.append(ResourceIssue(self.kind.upper() + '_OVERLAP', tid, group_id, other_id))
        return issues

    def validate(self, assignments, groups, time_model):
        issues = self.structure_issues({g.group_id for g in groups}, time_model)
        if issues:
            return issues
        seen = {}
        for gid, placement in assignments.items():
            if (isinstance(placement, (tuple, list)) and len(placement) == 4
                    and all(type(v) is int for v in placement[1:])):
                _, day, start, end = placement
                issues.extend(self.placement_issues(gid, day, start, end, seen))
                seen[gid] = placement
        return issues

    def to_data(self):
        return dict(kind=self.kind, enabled=self.enabled, resources=[dict(id=t.id, label=t.label,
                    availability=None if t.availability is None else [list(w) for w in t.availability])
                    for t in self.resources], memberships=[dict(group_id=g, resource_ids=None if t is None else list(t))
                    for g, t in self.memberships])

    @classmethod
    def from_data(cls, data):
        """Strict versioned boundary; never drop unknown fields or bad references."""
        if (not isinstance(data, dict) or set(data) != {'kind', 'enabled', 'resources', 'memberships'}
                or data['kind'] not in RESOURCE_KINDS or type(data['enabled']) is not bool
                or not isinstance(data['resources'], list) or not isinstance(data['memberships'], list)):
            raise ValueError('Unsupported or malformed resource catalog')
        resources, memberships = [], []
        for t in data['resources']:
            if (not isinstance(t, dict) or set(t) != {'id', 'label', 'availability'}
                    or not _visible(t['id']) or not _visible(t['label'])
                    or (t['availability'] is not None and not isinstance(t['availability'], list))):
                raise ValueError('Malformed resource')
            windows = t['availability']
            if windows is not None and any(not isinstance(w, list) or len(w) != 3
                    or any(type(v) is not int for v in w) for w in windows):
                raise ValueError('Malformed availability')
            resources.append(Resource(t['id'], t['label'], None if windows is None else tuple(tuple(w) for w in windows)))
        for member in data['memberships']:
            if (not isinstance(member, dict) or set(member) != {'group_id', 'resource_ids'}
                    or not _visible(member['group_id'])
                    or (member['resource_ids'] is not None and (not isinstance(member['resource_ids'], list)
                        or any(not _visible(r) for r in member['resource_ids'])))):
                raise ValueError('Malformed session membership')
            memberships.append((member['group_id'], None if member['resource_ids'] is None else tuple(member['resource_ids'])))
        return cls(data['kind'], data['enabled'], tuple(resources), tuple(memberships))


def _visible(value):
    return (isinstance(value, str) and 0 < len(value) <= 120 and value == value.strip()
            and not any(unicodedata.category(c).startswith('C') for c in value))


RESOURCE_KINDS = ('teacher', 'student_group', 'student')


@dataclass(frozen=True)
class SchedulingResources:
    catalogs: tuple[ResourceCatalog, ...] = ()

    def catalog(self, kind):
        return next((c for c in self.catalogs if c.kind == kind), ResourceCatalog(kind))

    def with_catalog(self, catalog):
        return SchedulingResources(tuple(c for c in self.catalogs if c.kind != catalog.kind) + (catalog,))

    def structure_issues(self, group_ids, time_model):
        if len({c.kind for c in self.catalogs}) != len(self.catalogs):
            return [ResourceIssue('DUPLICATE_RESOURCE_KIND')]
        return [i for c in self.catalogs for i in c.structure_issues(group_ids, time_model)]

    def placement_issues(self, group_id, day, start, end, assignments):
        return [i for c in self.catalogs for i in c.placement_issues(group_id, day, start, end, assignments)]

    def validate(self, assignments, groups, time_model):
        issues = self.structure_issues({g.group_id for g in groups}, time_model)
        if issues:
            return issues
        return [i for c in self.catalogs for i in c.validate(assignments, groups, time_model)]

    def to_data(self):
        return dict(version=1, catalogs=[c.to_data() for c in sorted(self.catalogs, key=lambda c: c.kind)])

    @classmethod
    def from_data(cls, data):
        if (not isinstance(data, dict) or set(data) != {'version', 'catalogs'}
                or type(data['version']) is not int or data['version'] != 1
                or not isinstance(data['catalogs'], list)):
            raise ValueError('Unsupported or malformed resource contract')
        return cls(tuple(ResourceCatalog.from_data(c) for c in data['catalogs']))
