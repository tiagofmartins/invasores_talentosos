from bokeh.application import Application
from bokeh.application.handlers.function import FunctionHandler
from bokeh.layouts import column
from bokeh.models import ColumnDataSource, Div, Slider
from bokeh.plotting import figure
from bokeh.server.server import Server


class Dashboard:

    def __init__(self, buffer):
        self.buffer = buffer


    def make_document(self, doc):

        layout = []

        snapshot = self.buffer.snapshot()

        for sensor_name in snapshot.keys():

            source = ColumnDataSource(
                data={
                    "x": [],
                    "signal": [],
                    "threshold": [],
                }
            )

            plot = figure(
                title=sensor_name,
                width=900,
                height=250,
                #x_axis_type="linear",
                x_axis_label="Sample"
            )

            plot.line(
                "x",
                "signal",
                source=source,
                line_width=2,
                legend_label="Signal",
            )

            plot.line(
                "x",
                "threshold",
                source=source,
                line_width=2,
                line_dash="dashed",
                line_color="red",
                legend_label="Threshold",
            )


            #value_div = Div(
            #    text="Current value: 0.000"
            #)

            status_div = Div(
                text="Status: INACTIVE"
            )


            slider = Slider(
                title="Threshold",
                start=0,
                end=1,
                value=snapshot[sensor_name]["threshold"],
                step=0.01,
            )


            slider.on_change(
                "value",
                lambda attr, old, new, s=sensor_name:
                    self.buffer.set_threshold(s, new)
            )


            def update(
                sensor=sensor_name,
                src=source,
                #value=value_div,
                status=status_div
            ):

                data = self.buffer.snapshot()[sensor]

                n = len(data["signal"])

                src.data = {
                    #"x": data["time"],
                    "x": list(range(n)),
                    "signal": data["signal"],
                    "threshold": [data["threshold"]] * n
                    #"threshold": [
                    #    data["threshold"]
                    #] * len(data["signal"])
                }


                #value.text = (
                #    f"<b>Current:</b> "
                #    f"{data['current']:.3f}"
                #)


                status.text = (
                    "<b>Status:</b> "
                    "<span style='color:green'>ACTIVE</span>"
                    if data["active"]
                    else
                    "<b>Status:</b> "
                    "<span style='color:red'>INACTIVE</span>"
                )


            doc.add_periodic_callback(
                update,
                50
            )


            layout.append(
                column(
                    plot,
                    slider,
                    #value_div,
                    status_div
                )
            )


        doc.add_root(
            column(*layout)
        )



def run_dashboard(buffer):

    dashboard = Dashboard(buffer)


    server = Server(
        {
            "/": Application(
                FunctionHandler(
                    dashboard.make_document
                )
            )
        },
        port=5006,
    )


    server.start()

    print(
        "Dashboard running at http://localhost:5006"
    )

    server.io_loop.start()