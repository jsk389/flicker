import numpy as np
import matplotlib.pyplot as plt
from noisy_plane import generate_samples, generate_samples_log, \
        lnlike, lnlikeH, lnlikeHF
from model import model1, model, load_data
import emcee
import triangle
import sys
import h5py

def lnprior_extra(pars, mm=False):
    if -10 < pars[0] < 10 and -10 < pars[1] < 10 and -100 < pars[2] < 100 \
            and -100 < pars[3] < 100:
        return 0., 0.
    return -np.inf, None

# def lnprior(pars, mm=False):
#     if -1e6 < pars[0] < 1e6 and -1e6 < pars[1] < 1e6 and -1e6 < pars[2] < 1e6:
#         return 0., 0.
#      return -np.inf, None

def lnprob(pars, samples, obs, u, extra, f):
# #     if extra:
#     print pars
#     pars[-2] = 1.2
#     print pars
#     print lnlikeHF(pars, samples, obs, u, extra=extra) + \
#             lnprior_extra(pars)
#     raw_input('tetner')
#     print lnlikeHF(pars, samples, obs, u, extra=extra) + \
#             lnprior_extra(pars)
    return lnlikeHF(pars, samples, obs, u, extra=extra) + \
            lnprior_extra(pars)
#     elif f:
#         print extra, f
#         return lnlikeHF(pars, samples, obs, u, extra=extra) + lnprior(pars)
#     else:
#         return lnlikeH(pars, samples, obs, u) + lnprior(pars)

def MCMC(whichx, nsamp, fname, nd, extra, f, bigdata, burnin=500, run=1000):
    """
    nsamp (int) = number of samples.
    whichx (str) = logg or rho.
    fname (str) = the name for saving all output
    nd (int) = number of data points (for truncation).
    If this is zero, all the data are used.
    bigdata (boolean) which data file to use.
    """

    # set initial parameters
    if extra:
        rho_pars = [-1.793214679, 5.34215688, 0.02334097, .0002600777]
        logg_pars = [-1.02143776, 5.69156647, .24239756, .049233887]
    else:
        rho_pars = [-1.69293833, 5.1408906, .0065]
        logg_pars = [-1.05043614, 5.66819525, .0065]
    pars_init = logg_pars
    if whichx == "rho":
        pars_init = rho_pars

    # load the data
    x, y, xerr, yerr = load_data(whichx, nd=nd, bigdata=False)

    # format data and generate samples
    obs = np.vstack((x, y))
    u = np.vstack((xerr, yerr))
    up = np.vstack((xerr, yerr))
    um = np.vstack((xerr*.5, yerr*.5))
    s = generate_samples(obs, u, nsamp)

    # set up and run emcee
    ndim, nwalkers = len(pars_init), 32
    pos = [pars_init + 1e-4*np.random.randn(ndim) for i in range(nwalkers)]
    sampler = emcee.EnsembleSampler(nwalkers, ndim, lnprob,
                                    args=(s, obs, u, extra, f))
    print "burning in..."
    pos, _, _, _ = sampler.run_mcmc(pos, burnin)
    sampler.reset()
    print "production run..."
    sampler.run_mcmc(pos, run)

    # load likelihood
    lls = sampler.blobs
    flat_lls = np.reshape(lls, (np.shape(lls)[0]*np.shape(lls)[1]))
    samp = np.vstack((sampler.chain[:, :, :].reshape(-1, ndim).T, flat_lls)).T

    sa = samp.T[0]
    print type(sa)
    print np.isfinite(sa)
    print sa
    print np.shape(sa), np.shape(sa[np.isfinite(sa)])
    # save samples
    f = h5py.File("%s_samples_%s.h5" % (whichx, fname), "w")
    data = f.create_dataset("samples", np.shape(samp))
    data[:, 0] = samp[:, 0]
    data[:, 1] = samp[:, 1]
    data[:, 2] = samp[:, 2]
    data[:, 3] = samp[:, 3]
    print "samp shape = ", np.shape(samp), np.shape(data)
    if extra:
        data[:, 4] = samp[:, 4]
    f.close()

def make_plots(whichx, fname):

    x, y, xerr, yerr = load_data(whichx)

    with h5py.File("%s_samples_%s.h5" % (whichx, fname)) as f:
        samp = f["samples"][:, :-1]

    if fname == "f_extra" or "short":
        m, c, ln_sig, lnf = map(lambda v: (v[1], v[2]-v[1], v[1]-v[0]),
                   zip(*np.percentile(samp, [16, 50, 84], axis=0)))
        pars = [m[0], c[0], ln_sig[0], lnf[0]]
        labels = ["$m$", "$c$", "$\sigma$", "$f$"]
    else:
        m, c, ln_sig = map(lambda v: (v[1], v[2]-v[1], v[1]-v[0]),
                   zip(*np.percentile(samp, [16, 50, 84], axis=0)))
        pars = [m[0], c[0], ln_sig[0]]
        labels = ["$m$", "$c$", "$\ln(\sigma)$"]

    print pars

    plt.clf()
    fig = triangle.corner(samp, labels=labels)
    fig.savefig("triangle_%s_%s" % (whichx, fname))

if __name__ == "__main__":
    whichx = str(sys.argv[1])
    fname = str(sys.argv[2])  # "f_extra"
    if fname == "f_extra" or "short": extra, f = True, True
#     elif fname == "short": extra, f = True, True
    elif fname == "f": extra, f = False, True
    else: extra, f = False, False
    nd = 0 # set to zero to use all the data
    ns, bi, r = 2, 100, 2000
#     ns, bi, r = 500, 100, 5000
    MCMC(whichx, ns, fname, nd, extra, f, bigdata=False, burnin=bi, run=r)
    make_plots(whichx, fname)
