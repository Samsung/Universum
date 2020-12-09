from docutils import nodes
from docutils.parsers.rst import Directive
from docutils.parsers.rst.directives import unchanged


class CollapsibleNode(nodes.General, nodes.Element):
    pass


def visit_collapsible_node(self, node):
    self.body.append(f"""
<input type="checkbox" id="collapsible" class="hide">
<label for="collapsible">
    <span class="sectionLbl"><b>{ node["header"] }</b></span>
</label>
<div>
""")


def depart_collapsible_node(self, node):
    self.body.append("""
</div>
<span class="nl">
</span>
""")


class CollapsibleDirective(Directive):
    has_content = True
    option_spec = {'header': unchanged}

    def run(self):
        collapsible_node = CollapsibleNode('\n'.join(self.content),
                                           header=self.options.get("header", "Click here to show/hide"))
        self.state.nested_parse(self.content, self.content_offset, collapsible_node)

        return [collapsible_node]


def setup(app):
    app.add_node(CollapsibleNode, html=(visit_collapsible_node, depart_collapsible_node))
    app.add_directive('collapsible', CollapsibleDirective)

    return {
        'version': '0.1',
        'parallel_read_safe': True,
        'parallel_write_safe': True,
    }
