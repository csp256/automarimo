# /// script
# requires-python = ">=3.13"
# dependencies = [
#     "marimo>=0.21.1",
#     "matplotlib==3.10.8",
#     "numpy==2.4.3",
# ]
# ///

import marimo

__generated_with = "0.21.1"
app = marimo.App(width="medium")

with app.setup:
    import marimo as mo
    import numpy as np
    import matplotlib.pyplot as plt


@app.cell(hide_code=True)
def _():
    mo.md(r"""
    ## Run the cells in order with: **Shift + Enter**
    """)
    return


@app.cell
def _():
    theta = np.arange(0, 2*np.pi, 0.01)
    return (theta,)


@app.cell
def _(theta):
    plt.plot(theta, np.sin(theta), label="sin")
    plt.plot(theta, np.cos(theta), label="cos")
    plt.legend()
    plt.grid(True)
    plt.title('Basic plotting')
    plt.xlabel(r'$\Theta$ [radians]')
    plt.ylabel(None)
    return


@app.cell
def _():
    return


if __name__ == "__main__":
    app.run()
