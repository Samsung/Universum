from docutils import nodes
from docutils.parsers.rst import Directive
from docutils.parsers.rst.directives import unchanged

collapsible_id_counter = 0


class CollapsibleNode(nodes.General, nodes.Element):
    pass


def visit_collapsible_node(self, node):
    self.body.append(f"""
<input type="checkbox" id="{node["id"]}" class="hide">
<label for="{node["id"]}">{node["header"]} <span class="collapser">&#x276f;</span></label>
<div>
""")


def depart_collapsible_node(self, node):
    self.body.append("""
</div>
""")


def visit_container(self, node):  # Not displaying headers, unfortunately
    self.visit_container(node)


def depart_container(self, node):
    self.depart_container(node)


class CollapsibleDirective(Directive):
    has_content = True
    option_spec = {'header': unchanged}

    def run(self):
        global collapsible_id_counter
        collapsible_node = CollapsibleNode('\n'.join(self.content),
                                           id="collapsible-" + str(collapsible_id_counter),
                                           header=self.options.get("header", "Click here to show/hide"))
        collapsible_id_counter += 1
        self.state.nested_parse(self.content, self.content_offset, collapsible_node)

        return [collapsible_node]


def setup(app):
    app.add_node(CollapsibleNode,
                 html=(visit_collapsible_node, depart_collapsible_node),
                 latex=(visit_container, depart_container),
                 text=(visit_container, depart_container))
    app.add_directive('collapsible', CollapsibleDirective)

    return {
        'version': '0.1',
        'parallel_read_safe': True,
        'parallel_write_safe': True,
    }
