# -*- coding: utf-8 -*-
# <nbformat>3.0</nbformat>

# <codecell>

from matplotlib.pylab import *
import numpy as np
from pymc import  *
from pymc.distributions.timeseries import *

from scipy.sparse import csc_matrix
from  scipy import optimize

# <markdowncell>

# Asset prices have time-varying volatility (variance of day over day `returns`). In some periods, returns are highly vaiable, and in others very stable. Stochastic volatility models model this with a latent volatility variable, modeled as a stochastic process. The following model is similar to the one described in the No-U-Turn Sampler paper, Hoffman (2011) p21.
# 
# $$ \sigma \sim Exponential(50) $$
# 
# $$ \nu \sim Exponential(.1) $$
# 
# $$ s_i \sim Normal(s_{i-1}, \sigma^{-2}) $$
# 
# $$ log(\frac{y_i}{y_{i-1}}) \sim t(\nu, 0, exp(-2 s_i)) $$
# 
# Here, $y$ is the daily return series and $s$ is the latent volatility process.

# <markdowncell>

# Build Model
# --------------

# <codecell>

model = Model()

# <markdowncell>

# Its easier to sample the scale of the volatility process innovations on a log scale, so we use `TransformedVar`.

# <codecell>

n = 400
returns = np.genfromtxt("data/SP500.csv")[-n:]

with model: 
    sigma, log_sigma = model.TransformedVar('sigma', Exponential(1./.02, testval = .1),
                 logtransform)

    nu = Exponential('nu', 1./10)

    
    s = GaussianRandomWalk('s', sigma**-2, shape = n)

    r = T('r', nu, lam = exp(-2*s), observed = returns)

# <markdowncell>

# Fit Model
# ------------
# To get a decent scale for the hamiltonaian sampler, we find the hessian at a point. However, the 2nd derivatives for the degrees of freedom are negative and thus not very informative, so we make an educated guess. The interactions between `log_sigma`/`nu` and `s` are also not very useful, so we set them to zero. 
# 
# The hessian matrix is also very sparse, so we make it a sparse matrix for faster sampling.

# <codecell>

H = model.d2logpc()

def hessian(point, nusd): 
    h = H(Point(point))
    h[1,1] = nusd**-2
    h[:2,2:] = h[2:,:2] = 0

    return csc_matrix(h)

# <markdowncell>

# The full MAP is a degenerate case wrt to sd and nu, so we find the MAP wrt the volatility process, keeping log_sd and nu constant at their default values. We use l_bfgs_b because it is more efficient for high dimensional functions (`s` has n elements)

# <codecell>

with model:
    start = find_MAP(vars = [s], fmin = optimize.fmin_l_bfgs_b)

# <markdowncell>

# We do a short initial run to get near the right area, then start again using a new hessian at the new starting point.

# <codecell>

with model: 
    step = HamiltonianMC(model.vars, hessian(start, 6))
    trace = sample(200, step, start, trace = model.vars + [sigma]) 

    start2 = trace.point(-1)
    step = HamiltonianMC(model.vars, hessian(start2, 6), path_length = 4.)
    trace = sample(8000, step, trace = trace) 

# <codecell>

#figsize(12,6)
title(str(s))
plot(trace[s][::10].T,'b', alpha = .01);

#figsize(12,6)
traceplot(trace, model.vars[:-1]);

# <codecell>

trace.samples.keys()

# <markdowncell>

# References
# -------------
#     1. Hoffman & Gelman. (2011). The No-U-Turn Sampler: Adaptively Setting Path Lengths in Hamiltonian Monte Carlo. http://arxiv.org/abs/1111.4246 

